#!/bin/bash -x
# Example Usage : ./delete-devices.sh <subnet> <docker-network-suffix-number>
# Example Usage : ./delete-devices.sh 192.168.1.0/24 1

SUBNET=$1
DOCKER_NETWORK_SUFFIX=$2
DOCKER_NETWORK=client-nw-$DOCKER_NETWORK_SUFFIX

VETH_OVS=w1-ovs
VETH_HOST=w1-host
INTF=ex0

BRIDGE=r1

# Check if Docker network exists
if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
  echo "Docker network $DOCKER_NETWORK does not exist"
  exit 1
fi

# Find and stop all containers in this network
echo "Finding and stopping containers in network $DOCKER_NETWORK..."
CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep "^c${DOCKER_NETWORK_SUFFIX}d")
for CONTAINER in $CONTAINERS; do
  echo "Stopping and removing container $CONTAINER"
  # Remove container from OVS bridge
  ./ovs-docker del-port $BRIDGE $INTF $CONTAINER || true
  docker kill $CONTAINER || true
done

# Get the first IP from the subnet
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
# Check if $FIRST_IP is added in $VETH_HOST interface

if ip addr show $VETH_HOST | grep -q "$FIRST_IP"; then
  echo "Removing IP $FIRST_IP from $VETH_HOST interface"
  ip addr del $FIRST_IP/24 dev $VETH_HOST
else
  echo "IP $FIRST_IP does not exist on $VETH_HOST interface"
fi


# Remove iptables rules
echo "Cleaning up iptables rules..."
export DEFAULT_DEV=$(ip route | awk '/default/ { print $5 }')

# Remove NAT rule
if iptables -t nat -C POSTROUTING -s $SUBNET -o $DEFAULT_DEV -j MASQUERADE >/dev/null 2>&1; then
  echo "Removing NAT rule for subnet $SUBNET"
  iptables -t nat -D POSTROUTING -s $SUBNET -o $DEFAULT_DEV -j MASQUERADE
fi

# Remove FORWARD rules
if iptables -C FORWARD -i $VETH_HOST -j ACCEPT >/dev/null 2>&1; then
  echo "Removing FORWARD rule for $VETH_HOST (input)"
  iptables -D FORWARD -i $VETH_HOST -j ACCEPT
fi

if iptables -C FORWARD -o $VETH_HOST -j ACCEPT >/dev/null 2>&1; then
  echo "Removing FORWARD rule for $VETH_HOST (output)"
  iptables -D FORWARD -o $VETH_HOST -j ACCEPT
fi

# Remove the Docker network
echo "Removing Docker network $DOCKER_NETWORK"
docker network rm $DOCKER_NETWORK || true

echo "Cleanup complete for network $DOCKER_NETWORK"