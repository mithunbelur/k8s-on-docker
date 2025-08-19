#!/bin/bash -x

set -e

# Include common_functions.sh for utility functions
source common_functions.sh

export DEFAULT_DEV=$(ip route | awk '/default/ { print $5 }')

ISP_ROUTER="isp"
ISP_HOST_IF="isp-host"
ISP_NS_IF="isp-ns"
ISP_HOST_IP="10.255.255.2/30"
ISP_NS_IP="10.255.255.1/30"

# Step 1: Create ISP router
create_isp_router $ISP_ROUTER $ISP_HOST_IF $ISP_NS_IF $ISP_HOST_IP $ISP_NS_IP $DEFAULT_DEV

# Step 2: Create K8S Edge Router
K8S_RTR="n1"
K8S_SUBNET="10.10.10.0/24"
K8S_EDGE_ROUTER_WAN_IP="10.0.1.1/30"
K8S_EDGE_ROUTER_GW_IP="10.0.1.2/30"

create_edge_router_and_link_to_isp_router $K8S_RTR $ISP_ROUTER $K8S_EDGE_ROUTER_WAN_IP $K8S_EDGE_ROUTER_GW_IP

# Step 3: Create K8S LAN network with single node
create_lan_network_and_link_to_edge_router $K8S_RTR "a" $K8S_SUBNET
create_cluster_nodes_in_lan_subnet $K8S_RTR "a" $K8S_SUBNET 1

# Step 4: Setup single node as control plane (with workloads allowed)
CONTROL_NODE=${K8S_RTR}"a1"
docker exec -it $CONTROL_NODE bash -c "/root/k8s-setup.sh control-plane"

echo "Single node cluster setup complete."

# Copy kubeconfig for local kubectl access
mkdir -p ~/.kube
docker exec -it $CONTROL_NODE cat /root/.kube/config > ~/.kube/config 2>/dev/null

# Setup routing for cluster access
ip route add $K8S_SUBNET via 10.255.255.1 dev isp-host
ip netns exec $ISP_ROUTER ip route add $K8S_SUBNET via 10.0.1.1 dev ${K8S_RTR}-wan1

echo "Single node Kubernetes cluster is ready!"
echo "You can access it using: kubectl get nodes"
