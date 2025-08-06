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
create_customer_edge_router_and_link_to_isp_router "c1" $ISP_ROUTER "10.0.1.1/30" "10.0.1.2/30"
#create_customer_edge_router_and_link_to_isp_router "c2" $ISP_ROUTER "10.0.2.1/30" "10.0.2.2/30"

#Step 3: Create Customer LAN networks and link to edge router
create_customer_lan_network_and_link_to_edge_router "c1" "192.168.11.0/24" "192.168.12.0/24"
#create_customer_lan_network_and_link_to_edge_router "c2" "192.168.21.0/24" "192.168.22.0/24"

#Step 4: Create Customer Devices(docker containers)
create_customer_devices_in_lan_subnet "c1" "a" "192.168.11.0/24" 2
create_customer_devices_in_lan_subnet "c1" "b" "192.168.12.0/24" 2

#create_customer_devices_in_lan_subnet "c2" "a" "192.168.21.0/24" 2
#create_customer_devices_in_lan_subnet "c2" "b" "192.168.22.0/24" 2

# Step 4: Add static routes in ISP router for customer subnets
#add_isp_routes_for_customer $ISP_ROUTER "ovsrtr1" "192.168.1.0/24" "192.168.2.0/24"
#add_isp_routes_for_customer $ISP_ROUTER "ovsrtr2" "192.168.3.0/24" "192.168.4.0/24"

# Step 5: Add host routes via ISP router so return traffic/NAT works
#add_host_routes_for_customer "veth_isp_host_host" "10.255.255.1/30" "192.168.1.0/24" "192.168.2.0/24" "192.168.3.0/24" "192.168.4.0/24"

# Step 6: Add SNAT on edge router WAN interfaces
#add_customer_snat "ovsrtr1" "wan1"
#add_customer_snat "ovsrtr2" "wan1"

# Step 7: Create K8s router and connect to ISP
#create_k8s_router "k8s-netns-rtr" $ISP_ROUTER "10.200.0.0/30" "10.200.0.2/30" "10.200.0.1/30"

# Step 8: Create GRE tunnel between ovsrtr1 and K8s router
#create_gre_tunnel "ovsrtr1" "k8s-netns-rtr" "10.0.1.1" "10.200.0.2" "172.16.100.1/30" "172.16.100.2/30" "169.254.1.1/32" "192.168.1.0/24" "192.168.2.0/24"

# Step 9: Create GRE tunnel between ovsrtr2 and K8s router (optional)
#create_gre_tunnel "ovsrtr2" "k8s-netns-rtr" "10.0.2.1" "10.200.0.2" "172.16.101.1/30" "172.16.101.2/30" "169.254.1.1/32" "192.168.3.0/24" "192.168.4.0/24"

#echo "Setup complete with K8s router and GRE tunnels."
#echo "- Edge routers (ovsrtr1, ovsrtr2) have SNAT configured on wan1"
#echo "- K8s router (k8s-netns-rtr) connected to ISP"
#echo "- GRE tunnels established for special traffic to 169.254.1.1"
#echo "- Customer devices can reach K8s services via GRE, other traffic via NAT"