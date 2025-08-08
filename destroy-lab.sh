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
K8S_RTR="n1"

delete_devices_in_lan_subnet "c1" "a"
delete_devices_in_lan_subnet "c1" "b"

delete_devices_in_lan_subnet "c2" "a"
delete_devices_in_lan_subnet "c2" "b"

delete_lan_network "c1" "a"
delete_lan_network "c1" "b"

delete_lan_network "c2" "a"
delete_lan_network "c2" "b"

delete_edge_router "c1"
delete_edge_router "c2"

#Deleting cluster
delete_cluster_nodes_in_lan_subnet $K8S_RTR "a"
delete_lan_network $K8S_RTR "a"
delete_edge_router $K8S_RTR

delete_isp_router $ISP_ROUTER
