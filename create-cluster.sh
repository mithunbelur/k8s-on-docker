#!/bin/bash -x

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

if ! ip link show $VETH_OVS >/dev/null 2>&1; then
  echo "Creating veth pair $VETH_OVS and $VETH_HOST"
  ip link add $VETH_OVS type veth peer $VETH_HOST
  ip link set $VETH_OVS up
  ip link set $VETH_HOST up
  ip addr add 10.10.10.1/24 dev $VETH_HOST
else
  echo "Veth pair $VETH_OVS and $VETH_HOST already exists"
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

export DEFAULT_DEV=`ip route | awk '/default/ { print $5 }'`

# Check if the iptables rule for NAT exists, if not add it
if ! iptables -t nat -C POSTROUTING -s 10.10.10.0/24 -o $DEFAULT_DEV -j MASQUERADE >/dev/null 2>&1; then
  echo "Adding iptables rule for NAT"
  iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o $DEFAULT_DEV -j MASQUERADE
else
  echo "NAT rule already exists"
fi

# Create container for the control plane
CONTROL_NODE="ctrl"
if docker ps -a --format '{{.Names}}' | grep -q "$CONTROL_NODE"; then
  echo "Container $CONTROL_NODE already exists, skipping creation"
else
  echo "Creating container $CONTROL_NODE"
  # Create the control plane container with necessary configurations
  docker run -it -d --rm --name "$CONTROL_NODE" -m 4g \
    --cap-add=SYS_PTRACE --privileged \
    --network $DOCKER_NETWORK \
    -v /boot:/boot -v /lib/modules:/lib/modules -v $(pwd):/root \
    --hostname "ctrl" \
    -e "NODE_NAME=ctrl" \
    -e "CLUSTER_SIZE=$CLUSTER_SIZE" \
    localhost/kubeadm-fedora:v1.0

  ./ovs-docker add-port $BRIDGE $INTF $CONTROL_NODE --ipaddress=10.10.10.10/24

  docker exec -it $CONTROL_NODE ip route del default
  docker exec -it $CONTROL_NODE ip route add default via 10.10.10.1 dev $INTF
fi

# Loop over cluster size and create containers
#docker run -it -d --rm -v /boot:/boot -v /lib/modules:/lib/modules  --name wkr1 --cap-add=SYS_PTRACE --privileged --network opsramp-gw  mithunbs/kubeadm-fedora:v1.0
for i in $(seq 1 $CLUSTER_SIZE); do
  CONTAINER_NAME="wkr$i"
  if ! docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
    echo "Creating container $CONTAINER_NAME"
    docker run -it -d --rm --name "$CONTAINER_NAME" -m 4g \
      --cap-add=SYS_PTRACE --privileged \
      --network $DOCKER_NETWORK \
      -v /boot:/boot -v /lib/modules:/lib/modules -v $(pwd):/root \
      --hostname "wkr$i" \
      -e "NODE_NAME=wkr$i" \
      -e "CLUSTER_SIZE=$CLUSTER_SIZE" \
      localhost/kubeadm-fedora:v1.0
    
    ./ovs-docker add-port $BRIDGE $INTF $CONTAINER_NAME --ipaddress=10.10.10.$((i + 10))/24

    docker exec -it $CONTAINER_NAME ip route del default
    docker exec -it $CONTAINER_NAME ip route add default via 10.10.10.1 dev $INTF

  else
    echo "Container $CONTAINER_NAME already exists, skipping creation"
  fi
done

docker exec -it $CONTROL_NODE bash -c "/root/k8s-setup.sh control-plane"

echo "Cluster setup complete. Use the join command from $CONTROL_NODE/join-command.sh to add worker nodes."
#For worker nodes, run the following command:
for i in $(seq 1 $CLUSTER_SIZE); do
  CONTAINER_NAME="wkr$i"
  docker exec -it $CONTAINER_NAME bash -c "/root/k8s-setup.sh worker-node"
done

echo "Worker nodes have been configured and joined to the cluster."

# Copy kubeconfig for local kubectl access
mkdir -p ~/.kube
docker exec -it ctrl cat /root/.kube/config > ~/.kube/config 2>/dev/null

echo "Ready! Run: kubectl get nodes"

echo "You can now use kubectl to manage your cluster."
