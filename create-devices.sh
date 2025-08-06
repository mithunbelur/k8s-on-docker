#!/bin/bash -x
# Example Usage : ./create-devices.sh <No-of-Devices> <subnet> <docker-network-suffix-number>
# Example Usage : ./create-devices.sh 3 192.168.1.0/24 1

DEVICE_SIZE=$1
SUBNET=$2 # SUBNET will be in the form of 192.168.1.0/24
DOCKER_NETWORK_SUFFIX=$3
DOCKER_NETWORK=client-nw-$DOCKER_NETWORK_SUFFIX

VETH_OVS=cr1-ovs
VETH_HOST=cr1-host
INTF=ex0

BRIDGE=cr1

if [ -z "$DEVICE_SIZE" ] || [ -z "$SUBNET" ]; then
  echo "Usage: $0 <device-size> <subnet>"
  exit 1
fi

if [ "$DEVICE_SIZE" -lt 1 ]; then
  echo "Device size must be at least 1"
  exit 1
fi

# Check if Docker network exists, if not create it
if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
  echo "Creating Docker network $DOCKER_NETWORK"
  docker network create $DOCKER_NETWORK
else
  echo "Docker network $DOCKER_NETWORK already exists"
fi

# Check if OVS bridge exists, if not create it
if ! ovs-vsctl br-exists $BRIDGE >/dev/null 2>&1; then
  echo "Creating OVS bridge $BRIDGE"
  ovs-vsctl add-br $BRIDGE
else
  echo "OVS bridge $BRIDGE already exists"
fi


#Get First IP from the subnet by first converting CIDR to integer and then add 1
IFS='/' read -r IP PREFIX <<< "$SUBNET"
IFS='.' read -r -a OCTETS <<< "$IP"
IP_INT=$(( 
    (${OCTETS[0]} << 24) + 
    (${OCTETS[1]} << 16) + 
    (${OCTETS[2]} << 8) + 
    ${OCTETS[3]} ))
FIRST_IP_INT=$(( IP_INT + 1 ))
FIRST_IP="$(( (${FIRST_IP_INT} >> 24) & 255 )).$(( (${FIRST_IP_INT} >> 16) & 255 )).$(( (${FIRST_IP_INT} >> 8) & 255 )).$(( ${FIRST_IP_INT} & 255 ))"
echo "First IP in the subnet is $FIRST_IP"

if ! ip link show $VETH_OVS >/dev/null 2>&1; then
  echo "Creating veth pair $VETH_OVS and $VETH_HOST"
  ip link add $VETH_OVS type veth peer $VETH_HOST
  ip link set $VETH_OVS up
  ip link set $VETH_HOST up
else
  echo "Veth pair $VETH_OVS and $VETH_HOST already exists"
fi

# Check if $FIRST_IP is added in $VETH_HOST interface
if ! ip addr show $VETH_HOST | grep -q "$FIRST_IP"; then
  echo "Adding IP $FIRST_IP to $VETH_HOST interface"
  ip addr add $FIRST_IP/24 dev $VETH_HOST
else
  echo "IP $FIRST_IP already exists on $VETH_HOST interface"
fi

ovs-vsctl --may-exist add-port $BRIDGE $VETH_OVS

if ! iptables -C FORWARD -i $VETH_HOST -j ACCEPT >/dev/null 2>&1; then
  echo "Adding iptables rules for $VETH_HOST"
  iptables -I FORWARD 1 -i $VETH_HOST -j ACCEPT
fi
if ! iptables -C FORWARD -o $VETH_HOST -j ACCEPT >/dev/null 2>&1; then
  echo "Adding iptables rules for $VETH_HOST"
  iptables -I FORWARD 1 -o $VETH_HOST -j ACCEPT
fi
export DEFAULT_DEV=$(ip route | awk '/default/ { print $5 }')
# Check if the iptables rule for NAT exists, if not add it
if ! iptables -t nat -C POSTROUTING -s $SUBNET -o $DEFAULT_DEV -j MASQUERADE >/dev/null 2>&1; then
  echo "Adding iptables rule for NAT"
  iptables -t nat -A POSTROUTING -s $SUBNET -o $DEFAULT_DEV -j MASQUERADE
else
  echo "Iptables rule for NAT already exists"
fi

# Create device containers
echo "Creating device containers..."
NEXT_IP_INT=$FIRST_IP_INT
for i in $(seq 1 $DEVICE_SIZE); do
  CONTAINER_NAME="c${DOCKER_NETWORK_SUFFIX}d$i" # Container name format c1d1 c1d2 etc.
  if docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
    echo "Container $CONTAINER_NAME already exists, skipping creation"
  else
    echo "Creating container $CONTAINER_NAME"
    docker run -it -d --rm --name "$CONTAINER_NAME" --cap-add=NET_ADMIN --network $DOCKER_NETWORK localhost/client-device:v1.0

    NEXT_IP_INT=$(( NEXT_IP_INT + 1 ))
    NEXT_IP="$(( (${NEXT_IP_INT} >> 24) & 255 )).$(( (${NEXT_IP_INT} >> 16) & 255 )).$(( (${NEXT_IP_INT} >> 8) & 255 )).$(( ${NEXT_IP_INT} & 255 ))"

    ./ovs-docker add-port $BRIDGE $INTF $CONTAINER_NAME --ipaddress=$NEXT_IP/24

    docker exec -it $CONTAINER_NAME ip route del default
    docker exec -it $CONTAINER_NAME ip route add default via $FIRST_IP dev $INTF
  fi
done