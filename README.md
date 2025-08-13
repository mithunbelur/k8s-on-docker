# Kubernetes on Docker Lab Environment

This project creates a Kubernetes cluster using Docker containers with custom networking to simulate a real-world onprem to cloud cluster environment.

## Environment Overview

The lab environment consists of client devices and a Kubernetes cluster all interconnected through a simulated ISP network topology. This setup allows for realistic testing of network policies, service discovery, and inter-node communication patterns within a containerized infrastructure.

## 1. EC2 Preparation Script

Run the preparation script to download necessary packages, setup Docker registry, and build required images:

```bash
# Make the script executable
chmod +x prepare-ec2.sh

# Run the preparation script
./prepare-ec2.sh
```

The preparation script will:
- Install Docker and Kubernetes tools
- Setup local Docker registry
- Build Kubernetes node images
- Build test container/pod images
- Configure network prerequisites

## 2. Setting Up Lab Environment

The lab environment follows the architecture defined in `network-diagram.puml`. To set up the environment:

```bash
# Deploy the lab infrastructure
./setup-lab.sh

# Verify cluster is running
kubectl get nodes

# Check network topology
docker network ls
```

This will create:
- Multi-node Kubernetes cluster
- Simulated ISP network segments
- Client access points
- Network bridges as per diagram

## 3. Running Tests

Execute the test suite to validate the environment:

```bash
# To run all tests
cd tests
TEST_LOG_FILE=my_custom.log ./run_tests.sh

# To list and know how to run specific tests
TEST_LOG_FILE=my_custom.log ./run_tests.sh --help

```
