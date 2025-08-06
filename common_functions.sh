# Utility: create veth pair and set one end to namespace
function create_veth_ns_pair() {
    local veth_host=$1
    local veth_ns=$2
    local ns=$3
    ip link add $veth_host type veth peer name $veth_ns
    ip link set $veth_ns netns $ns
    ip link set $veth_host up
    ip netns exec $ns ip link set $veth_ns up
}

# Utility: create OVS bridge if missing
function ensure_ovs_bridge() {
    local bridge=$1
    if ! ovs-vsctl br-exists $bridge; then
        ovs-vsctl add-br $bridge
    fi
}

# Create the ISP router namespace and host uplink
function create_isp_router() {
    local isp_ns=$1
    local isp_host_if=$2
    local isp_ns_if=$3
    local isp_host_ip=$4
    local isp_ns_ip=$5
    local host_uplink_if=$6

    # Create namespace
    ip netns add $isp_ns

    # Create veth pair between ISP and host
    ip link add $isp_host_if type veth peer name $isp_ns_if
    ip link set $isp_ns_if netns $isp_ns
    ip link set $isp_host_if up
    ip netns exec $isp_ns ip link set $isp_ns_if up

    # Assign IPs
    ip addr add $isp_host_ip dev $isp_host_if
    ip netns exec $isp_ns ip addr add $isp_ns_ip dev $isp_ns_if

    # Enable forwarding
    ip netns exec $isp_ns sysctl -w net.ipv4.ip_forward=1

    # Set up default route in ISP to host
    ip netns exec $isp_ns ip route add default via ${isp_host_ip%%/*} dev $isp_ns_if

    # Host uplink for NAT (ensure up)
    ip link set $host_uplink_if up
    sysctl -w net.ipv4.ip_forward=1

    ip netns exec $isp_ns iptables -t nat -A POSTROUTING -o $isp_ns_if -j MASQUERADE

    # NAT for internet on host
    iptables -t nat -A POSTROUTING -s $isp_ns_ip -o $host_uplink_if -j MASQUERADE
    iptables -I FORWARD 1 -i $isp_host_if -j ACCEPT
    iptables -I FORWARD 1 -o $isp_host_if -j ACCEPT
}

# function to delete ISP router namespace
function delete_isp_router() {
    local isp_ns=$1
    # Delete the namespace
    ip netns del $isp_ns
    # Delete the veth pair
    ip link del veth_${isp_ns}_host
    ip link del veth_${isp_ns}_ns
    # Remove iptables rules if they exist
    iptables -t nat -D POSTROUTING -s ${isp_ns}_ip -o $DEFAULT_DEV -j MASQUERADE 2>/dev/null || true
}

function create_customer_edge_router_and_link_to_isp_router() {
    local cust_ns=$1
    local isp_ns=$2
    local cust_isp_cust_ip=$3
    local cust_isp_isp_ip=$4

    # Create customer router namespace
    ip netns add $cust_ns

    # Create veth pair between customer and ISP
    local veth_cust_isp="t-${cust_ns}-wan1"
    local veth_isp_cust="${cust_ns}-wan1"
    ip link add $veth_cust_isp type veth peer name $veth_isp_cust
    ip link set $veth_cust_isp netns $cust_ns
    ip link set $veth_isp_cust netns $isp_ns

    # Rename in customer ns to wan1
    ip netns exec $cust_ns ip link set $veth_cust_isp name wan1
    # Rename in isp ns to keep original name
    # (no rename needed unless you want e.g. wan1-peer)

    # Assign point-to-point IPs
    ip netns exec $cust_ns ip addr add $cust_isp_cust_ip dev wan1
    ip netns exec $isp_ns ip addr add $cust_isp_isp_ip dev $veth_isp_cust
    ip netns exec $cust_ns ip link set wan1 up
    ip netns exec $isp_ns ip link set $veth_isp_cust up

    # Enable forwarding in customer router
    ip netns exec $cust_ns sysctl -w net.ipv4.ip_forward=1

    ip netns exec $cust_ns iptables -t nat -A POSTROUTING -o wan1 -j MASQUERADE

    # Set up default route in customer router to ISP
    ip netns exec $cust_ns ip route add default via ${cust_isp_isp_ip%%/*} dev wan1
}

function delete_customer_edge_router() {
    local cust_ns=$1
    # Delete the namespace
    ip netns del $cust_ns
    # Delete the veth pairs
    local veth_cust_isp="t-${cust_ns}-wan1"
    local veth_isp_cust="t-isp-${cust_ns}-wan1"
    ip link del $veth_cust_isp 2>/dev/null || true
    ip link del $veth_isp_cust 2>/dev/null || true
}

function create_customer_lan_network_and_link_to_edge_router() {
    local cust_ns=$1
    shift 1
    local subnets=("$@")

    # Create OVS bridge for the customer
    local bridge=${cust_ns}
    ensure_ovs_bridge $bridge

    # For each subnet, create router veth as lan1, lan2, ...
    local idx=1
    for subnet in "${subnets[@]}"; do
        # Get gateway IP for the subnet (e.g. 10.0.0.254 for 10.0.0.0/24)
        local gw_ip=$(get_last_ip_in_subnet $subnet)
        local veth_ovs="veth_${cust_ns}_lan${idx}"
        local veth_ns="veth_${cust_ns}_lan${idx}_ns"
        create_veth_ns_pair $veth_ovs $veth_ns $cust_ns
        # Rename in namespace
        local lan_name="lan${idx}"
        ip netns exec $cust_ns ip link set $veth_ns name $lan_name
        ovs-vsctl add-port $bridge $veth_ovs
        ip netns exec $cust_ns ip addr add ${gw_ip}/24 dev $lan_name
        ip netns exec $cust_ns ip link set $lan_name up
        idx=$((idx+1))
    done
}

#create_customer_devices_in_lan_subnet "c1" "a" "192.168.11.0/24" 2

function create_customer_devices_in_lan_subnet() {
    local cust_ns=$1
    local device_prefix=$2
    local subnet=$3
    local num_devices=$4
    DOCKER_NETWORK=${cust_ns}
    local intf="ex0"

    local gw_ip=$(get_last_ip_in_subnet $subnet)

    if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
        echo "Creating Docker network $DOCKER_NETWORK"
        docker network create $DOCKER_NETWORK
    else
        echo "Docker network $DOCKER_NETWORK already exists"
    fi

    # Create OVS bridge for the customer
    local bridge=${cust_ns}
    ensure_ovs_bridge $bridge

    IFS='/' read -r IP PREFIX <<< "$subnet"
    IFS='.' read -r -a OCTETS <<< "$IP"
    NEXT_IP_INT=$(( (${OCTETS[0]} << 24) + (${OCTETS[1]} << 16) + (${OCTETS[2]} << 8) + (${OCTETS[3]}) ))

    echo "Creating device containers..."
    for i in $(seq 1 $num_devices); do
        CONTAINER_NAME="${cust_ns}${device_prefix}$i" # Container name format c1a1 c1a2 etc.
        if docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
            echo "Container $CONTAINER_NAME already exists, skipping creation"
        else
            echo "Creating container $CONTAINER_NAME"
            docker run -it -d --rm --name "$CONTAINER_NAME" --cap-add=NET_ADMIN --network $DOCKER_NETWORK localhost/client-device:v1.0

            NEXT_IP_INT=$(( NEXT_IP_INT + 1 ))
            NEXT_IP="$(( (${NEXT_IP_INT} >> 24) & 255 )).$(( (${NEXT_IP_INT} >> 16) & 255 )).$(( (${NEXT_IP_INT} >> 8) & 255 )).$(( ${NEXT_IP_INT} & 255 ))"

            ./ovs-docker add-port $bridge $intf $CONTAINER_NAME --ipaddress=$NEXT_IP/24

            docker exec -it $CONTAINER_NAME ip route del default
            docker exec -it $CONTAINER_NAME ip route add default via $gw_ip dev $intf
        fi
    done
}

function get_last_ip_in_subnet() {
    local subnet=$1
    IFS='/' read -r IP PREFIX <<< "$subnet"
    IFS='.' read -r -a OCTETS <<< "$IP"
    IP_INT=$(( (${OCTETS[0]} << 24) + (${OCTETS[1]} << 16) + (${OCTETS[2]} << 8) + (${OCTETS[3]}) ))

    LAST_IP_INT=$(( IP_INT + (1 << (32 - PREFIX)) - 2 )) # -2 for network and broadcast addresses
    LAST_IP="$(( (${LAST_IP_INT} >> 24) & 255 )).$(( (${LAST_IP_INT} >> 16) & 255 )).$(( (${LAST_IP_INT} >> 8) & 255 )).$(( ${LAST_IP_INT} & 255 ))"
    echo $LAST_IP
}

# Add static routes for customer subnets in ISP router
function add_isp_routes_for_customer() {
    local isp_ns=$1
    local cust_ns=$2
    local subnets=("${@:3}")
    for idx in "${!subnets[@]}"; do
        local subnet="${subnets[$idx]}"
        local gw_ip=$(echo $subnet | sed 's|0/24|254|')
        local veth_isp_cust="veth_isp_${cust_ns}_wan1"
        ip netns exec $isp_ns ip route add $subnet via $gw_ip dev $veth_isp_cust
    done
}

# Add routes on host to reach customer subnets via ISP router
function add_host_routes_for_customer() {
    local isp_host_if=$1
    local isp_ns_ip=$2
    shift 2
    local subnets=("$@")
    for subnet in "${subnets[@]}"; do
        ip route add $subnet via ${isp_ns_ip%%/*} dev $isp_host_if
    done
}

# Add SNAT (masquerading) on customer router WAN interface
function add_customer_snat() {
    local cust_ns=$1
    local wan_if=$2
    ip netns exec $cust_ns iptables -t nat -A POSTROUTING -o $wan_if -j MASQUERADE
}

# Create K8s router namespace and connect it to the ISP
function create_k8s_router() {
    local k8s_ns=$1
    local isp_ns=$2
    local k8s_isp_net=$3      # e.g. 10.200.0.0/30
    local k8s_isp_k8s_ip=$4   # e.g. 10.200.0.2/30
    local k8s_isp_isp_ip=$5   # e.g. 10.200.0.1/30

    # Create K8s router namespace
    ip netns add $k8s_ns

    # Create veth pair between K8s and ISP
    local veth_k8s_isp="veth_${k8s_ns}_wan1"
    local veth_isp_k8s="veth_isp_${k8s_ns}_wan1"
    ip link add $veth_k8s_isp type veth peer name $veth_isp_k8s
    ip link set $veth_k8s_isp netns $k8s_ns
    ip link set $veth_isp_k8s netns $isp_ns

    # Rename in K8s ns to wan1
    ip netns exec $k8s_ns ip link set $veth_k8s_isp name wan1

    # Assign point-to-point IPs
    ip netns exec $k8s_ns ip addr add $k8s_isp_k8s_ip dev wan1
    ip netns exec $isp_ns ip addr add $k8s_isp_isp_ip dev $veth_isp_k8s
    ip netns exec $k8s_ns ip link set wan1 up
    ip netns exec $isp_ns ip link set $veth_isp_k8s up

    # Enable forwarding in K8s router
    ip netns exec $k8s_ns sysctl -w net.ipv4.ip_forward=1

    # Set up default route in K8s router to ISP
    ip netns exec $k8s_ns ip route add default via ${k8s_isp_isp_ip%%/*} dev wan1
}

# Create GRE tunnel between customer edge router and K8s router
function create_gre_tunnel() {
    local cust_ns=$1
    local k8s_ns=$2
    local cust_wan_ip=$3      # Customer WAN IP (without /30)
    local k8s_wan_ip=$4       # K8s WAN IP (without /30)
    local tunnel_cust_ip=$5   # Tunnel IP on customer side (with /30)
    local tunnel_k8s_ip=$6    # Tunnel IP on K8s side (with /30)
    local special_route=$7    # Special route to add (e.g., 169.254.1.1/32)
    shift 7
    local cust_subnets=("$@") # Customer subnets to route via tunnel from K8s side

    # Create GRE tunnel on customer side
    local gre_cust_name="gre-k8s"
    ip netns exec $cust_ns ip tunnel add $gre_cust_name mode gre local $cust_wan_ip remote $k8s_wan_ip ttl 255
    ip netns exec $cust_ns ip link set $gre_cust_name up
    ip netns exec $cust_ns ip addr add $tunnel_cust_ip dev $gre_cust_name
    ip netns exec $cust_ns ip route add $special_route dev $gre_cust_name

    # Create GRE tunnel on K8s side
    local gre_k8s_name="gre-${cust_ns}"
    ip netns exec $k8s_ns ip tunnel add $gre_k8s_name mode gre local $k8s_wan_ip remote $cust_wan_ip ttl 255
    ip netns exec $k8s_ns ip link set $gre_k8s_name up
    ip netns exec $k8s_ns ip addr add $tunnel_k8s_ip dev $gre_k8s_name

    # Add routes for customer subnets via tunnel on K8s side
    for subnet in "${cust_subnets[@]}"; do
        ip netns exec $k8s_ns ip route add $subnet dev $gre_k8s_name
    done
}
