#!/bin/bash

CLUSTER_SIZE=$1
BRIDGE=r1
VETH_HOST=r1-host
VETH_OVS=r1-ovs
INTF=ex0
DOCKER_NETWORK=bridge

if [ -z "$CLUSTER_SIZE" ]; then
  echo "Usage: $0 <cluster-size>"
  exit 1
fi

if [ "$CLUSTER_SIZE" -lt 1 ]; then
  echo "Cluster worker node size must be at least 1"
  exit 1
fi

# Delete all containers created by create-cluster.sh
echo "Deleting worker containers..."
for i in $(seq 1 $CLUSTER_SIZE); do
  CONTAINER_NAME="wkr$i"
  if docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
    echo "Removing container $CONTAINER_NAME"
    ./ovs-docker del-port $BRIDGE $INTF $CONTAINER_NAME
    docker kill $CONTAINER_NAME
  else
    echo "Container $CONTAINER_NAME doesn't exist, skipping deletion"
  fi
done

# Delete control plane container
CONTAINER_NAME="ctrl"
if docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
  echo "Removing container $CONTAINER_NAME"
  ./ovs-docker del-port $BRIDGE $INTF $CONTAINER_NAME
  docker kill $CONTAINER_NAME
else
  echo "Container $CONTAINER_NAME doesn't exist, skipping deletion"
fi

# Remove iptables rules
export DEFAULT_DEV=`ip route | awk '/default/ { print $5 }'`
echo "Removing iptables rules..."
if iptables -t nat -C POSTROUTING -s 10.10.10.0/24 -o $DEFAULT_DEV -j MASQUERADE >/dev/null 2>&1; then
  iptables -t nat -D POSTROUTING -s 10.10.10.0/24 -o $DEFAULT_DEV -j MASQUERADE
fi

if iptables -C FORWARD -i $VETH_HOST -j ACCEPT >/dev/null 2>&1; then
  iptables -D FORWARD -i $VETH_HOST -j ACCEPT
fi

if iptables -C FORWARD -o $VETH_HOST -j ACCEPT >/dev/null 2>&1; then
  iptables -D FORWARD -o $VETH_HOST -j ACCEPT
fi

# Delete OVS port and bridge
echo "Removing OVS configurations..."
if ovs-vsctl port-to-br $VETH_OVS >/dev/null 2>&1; then
  ovs-vsctl del-port $BRIDGE $VETH_OVS
fi

if ovs-vsctl br-exists $BRIDGE >/dev/null 2>&1; then
  echo "Deleting OVS bridge $BRIDGE"
  ovs-vsctl del-br $BRIDGE
fi

# Delete VETH pair
if ip link show $VETH_HOST >/dev/null 2>&1; then
  echo "Removing VETH pair $VETH_OVS and $VETH_HOST"
  ip link delete $VETH_HOST
fi

# Delete Docker network
#if docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
#  echo "Removing Docker network $DOCKER_NETWORK"
#  docker network rm $DOCKER_NETWORK
#fi

rm -rf ~/.kube

echo "Cleanup completed successfully"

