#!/bin/bash -x

set -e

# Include common_functions.sh for utility functions
source common_functions.sh

# Example usage

export DEFAULT_DEV=$(ip route | awk '/default/ { print $5 }')

ISP_ROUTER="isp"
ISP_HOST_IF="isp-host"
ISP_NS_IF="isp-ns"
ISP_HOST_IP="10.255.255.2/30"
ISP_NS_IP="10.255.255.1/30"

# Step 1: Create ISP router (args: ns, host_if, ns_if, host_ip/cidr, ns_ip/cidr, host uplink)
create_isp_router $ISP_ROUTER $ISP_HOST_IF $ISP_NS_IF $ISP_HOST_IP $ISP_NS_IP $DEFAULT_DEV

# Step 2: Create Customer Edge Router 1 and Edge Router 2
C1_EDGE_ROUTER_WAN_IP="10.1.1.1/30"
C1_EDGE_ROUTER_GW_IP="10.1.1.2/30"
C2_EDGE_ROUTER_WAN_IP="10.2.1.1/30"
C2_EDGE_ROUTER_GW_IP="10.2.1.2/30"

create_edge_router_and_link_to_isp_router "c1" $ISP_ROUTER $C1_EDGE_ROUTER_WAN_IP $C1_EDGE_ROUTER_GW_IP
create_edge_router_and_link_to_isp_router "c2" $ISP_ROUTER $C2_EDGE_ROUTER_WAN_IP $C2_EDGE_ROUTER_GW_IP

#Step 3: Create Customer LAN networks and link to edge router
create_lan_network_and_link_to_edge_router "c1" "a" "192.168.11.0/24" 
create_lan_network_and_link_to_edge_router "c1" "b" "192.168.12.0/24"

create_lan_network_and_link_to_edge_router "c2" "a" "192.168.21.0/24" 
create_lan_network_and_link_to_edge_router "c2" "b" "192.168.22.0/24"

#Step 4: Create Customer Devices(docker containers)
create_devices_in_lan_subnet "c1" "a" "192.168.11.0/24" 2
create_devices_in_lan_subnet "c1" "b" "192.168.12.0/24" 2

create_devices_in_lan_subnet "c2" "a" "192.168.21.0/24" 1
create_devices_in_lan_subnet "c2" "b" "192.168.22.0/24" 1


K8S_RTR="n1"
K8S_SUBNET="10.10.10.0/24"
K8S_EDGE_ROUTER_WAN_IP="10.0.1.1/30"
K8S_EDGE_ROUTER_GW_IP="10.0.1.2/30"

create_edge_router_and_link_to_isp_router $K8S_RTR $ISP_ROUTER $K8S_EDGE_ROUTER_WAN_IP $K8S_EDGE_ROUTER_GW_IP
create_lan_network_and_link_to_edge_router $K8S_RTR "a" $K8S_SUBNET
create_cluster_nodes_in_lan_subnet $K8S_RTR "a" $K8S_SUBNET 3

CONTROL_NODE=${K8S_RTR}"a1"

docker exec -it $CONTROL_NODE bash -c "/root/k8s-setup.sh control-plane"

echo "Cluster setup complete. Use the join command from $CONTROL_NODE/join-command.sh to add worker nodes."
#For worker nodes, run the following command:
# Get all docker containers that are worker nodes

CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep "^${K8S_RTR}a[0-9]*$")
for container in $CONTAINERS; do
    # skip if container is the control node
    if [[ "$container" == "$CONTROL_NODE" ]]; then
        continue
    fi
    docker exec -it $container bash -c "/root/k8s-setup.sh worker-node"
done

echo "Worker nodes have been configured and joined to the cluster."

# Copy kubeconfig for local kubectl access
mkdir -p ~/.kube
docker exec -it $CONTROL_NODE cat /root/.kube/config > ~/.kube/config 2>/dev/null

# With this, we can access the cluster using kubectl
ip route add $K8S_SUBNET via 10.255.255.1 dev isp-host
ip netns exec $ISP_ROUTER ip route add $K8S_SUBNET via 10.0.1.1 dev ${K8S_RTR}-wan1

# Step 8: Create GRE tunnel between ovsrtr1 and K8s router
#create_gre_tunnel "ovsrtr1" "k8s-netns-rtr" "10.0.1.1" "10.200.0.2" "172.16.100.1/30" "172.16.100.2/30" "169.254.1.1/32" "192.168.1.0/24" "192.168.2.0/24"

# Step 9: Create GRE tunnel between ovsrtr2 and K8s router (optional)
#create_gre_tunnel "ovsrtr2" "k8s-netns-rtr" "10.0.2.1" "10.200.0.2" "172.16.101.1/30" "172.16.101.2/30" "169.254.1.1/32" "192.168.3.0/24" "192.168.4.0/24"

#echo "Setup complete with K8s router and GRE tunnels."
#echo "- Edge routers (ovsrtr1, ovsrtr2) have SNAT configured on wan1"
#echo "- K8s router (k8s-netns-rtr) connected to ISP"
#echo "- GRE tunnels established for special traffic to 169.254.1.1"
#echo "- Customer devices can reach K8s services via GRE, other traffic via NAT"