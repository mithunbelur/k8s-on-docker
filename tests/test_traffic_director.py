#!/home/ubuntu/Developer/k8s-on-docker/tests/venv/bin/python3

"""
Traffic Director Test Cases

This module contains test cases for Traffic Director scenarios.
"""

import pytest
import time

from framework import HelmTestFramework
from framework.config import is_debug_enabled
from framework.logger import get_logger

logger = get_logger()

class TestTrafficDirector:
    """Test cases for Traffic Director scenarios"""
    
    @pytest.fixture(scope='class', autouse=True)
    def setup_and_teardown(self, request):
        """Setup and teardown for the entire test suite"""
        debug_enabled = is_debug_enabled()
        # Set framework on the class itself - no need to pass log_file anymore
        request.cls.framework = HelmTestFramework(debug=debug_enabled)
        
        # Cleanup before all tests
        #request.cls.framework.cleanup_helm_release()
        #request.cls.framework.cleanup_gateway_releases()
        
        yield
        
        # Cleanup after all tests
        #request.cls.framework.cleanup_helm_release()
        #request.cls.framework.cleanup_gateway_releases()
    
    def test_install_with_program_aws_route_table_true_no_table(self):
        """Test 1: Install with programAwsRouteTable=true but no awsRouteTable"""
        logger.info("Running Test 1: programAwsRouteTable=true without awsRouteTable")
        
        extra_args = "--set trafficDirectorController.programAwsRouteTable=true"
        result = self.framework.helm_install(extra_args)
        
        # Should fail with expected error message
        assert not result['success'], "Installation should have failed"
        
        expected_error = "awsRouteTable must be set or programAwsRouteTable must be false"
        error_output = result['stderr'] + result['stdout']
        assert expected_error in error_output, f"Expected error message not found. Output: {error_output}"
        
        logger.info("✓ Test 1 passed: Got expected error for missing awsRouteTable")
    
    def test_install_with_program_aws_route_table_true_no_irsa(self):
        """Test 2: Install with programAwsRouteTable=true and dummy awsRouteTable but no awsIrsaArn"""
        logger.info("Running Test 2: programAwsRouteTable=true with awsRouteTable but no awsIrsaArn")
        
        extra_args = (
            "--set trafficDirectorController.programAwsRouteTable=true "
            "--set trafficDirectorController.awsRouteTable=rtb-dummy123"
        )
        result = self.framework.helm_install(extra_args)
        
        # Should fail with expected error message
        assert not result['success'], "Installation should have failed"
        
        expected_error = "awsIrsaArn must be set or programAwsRouteTable must be false"
        error_output = result['stderr'] + result['stdout']
        assert expected_error in error_output, f"Expected error message not found. Output: {error_output}"
        
        logger.info("✓ Test 2 passed: Got expected error for missing awsIrsaArn")
    
    def test_install_with_program_aws_route_table_false(self):
        """Test 3: Install with programAwsRouteTable=false (should succeed)"""
        logger.info("Running Test 3: programAwsRouteTable=false")
        
        extra_args = "--set trafficDirectorController.programAwsRouteTable=false"
        result = self.framework.helm_install(extra_args)
        
        # Should succeed
        assert result['success'], f"Installation should have succeeded. Error: {result['stderr']}"
        
        logger.info("✓ Installation succeeded")
        
        # Wait 30 seconds as specified
        logger.info("Waiting 30 seconds before checking pods...")
        time.sleep(30)
        
        # Check if pods are up
        pods_ready = self.framework.wait_for_pods_ready(self.framework.namespace, timeout=90)
        assert pods_ready, "Pods should be running after installation"
        
        logger.info("✓ Test 3 passed: Installation successful and pods are running")

    def test_install_gateway_releases(self):
        """Test 4: Install 4 gateway helm releases in different namespaces"""
        logger.info("Running Test 4: Installing 4 gateway releases")
        
        # Install each gateway using the centralized configuration
        for i, gateway in enumerate(self.framework.gateways, 1):
            namespace = gateway['namespace']
            subnets = gateway['subnets']
            
            logger.info(f"Installing gateway {i}/4 in namespace {namespace} with subnets {subnets}")
            
            # Helm install command for gateway
            cmd = (
                f"helm install gw ../charts/target -n {namespace} --create-namespace "
                f"--set dp.image.repository=us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-images/trafficdirector "
                f"--set dp.image.tag=latest "
                f"--set target.image.repository=10.255.255.2:5000/http-udp-server "
                f"--set target.image.tag=latest "
                f"--set configmap.enabled=true "
                f"--set gatewaySubnet.enabled=true "
                f'--set "subnets={{{subnets}}}"'
            )
            
            result = self.framework.run_command(cmd)
            assert result['success'], f"Gateway installation failed for {namespace}. Error: {result['stderr']}"
            
            logger.info(f"✓ Gateway installed successfully in {namespace}")
        
        # Wait for all pods to be ready
        logger.info("Waiting for all gateway pods to be ready...")
        time.sleep(10)
        
        # Check each namespace for pod readiness
        for gateway in self.framework.gateways:
            namespace = gateway['namespace']
            logger.info(f"Checking pods in namespace {namespace}...")
            
            pods_ready = self.framework.wait_for_pods_ready(namespace, timeout=90)
            assert pods_ready, f"Pods should be running in namespace {namespace}"
            
            logger.info(f"✓ All pods ready in {namespace}")
        
        logger.info("✓ Test 4 passed: All 4 gateway releases installed successfully")

    def test_create_single_traffic_director_all_namespace_same_vip(self):
        """Test 5: Create Traffic Director CR and validate connectivity from customer devices"""
        logger.info("Running Test 5: Creating Traffic Director CR and validating connectivity")
        
        # First ensure gateways are installed (dependency on previous test)
        logger.info("Verifying gateway installations are present...")
        for gateway in self.framework.gateways:
            namespace = gateway['namespace']
            check_cmd = f"helm list -n {namespace} -q"
            result = self.framework.run_command(check_cmd)
            assert "gw" in result['stdout'], f"Gateway not found in namespace {namespace}. Run gateway installation test first."
        
        # Query and loop for all traffic director CRs and delete them
        # List of Traffic Director CRs
        cr_list_cmd = "kubectl get trafficdirector -n opsramp-sdn -o jsonpath='{.items[*].metadata.name}'"
        result = self.framework.run_command(cr_list_cmd)
        existing_crs = result['stdout'].split()
        logger.info(f"Found existing Traffic Director CRs: {existing_crs}")
        if existing_crs:
            logger.info("Cleaning up any existing Traffic Director CRs...")
            # This ensures we start fresh by deleting any existing CRs
            for cr_name in existing_crs:
                cleanup_cmd = f"kubectl delete trafficdirector {cr_name} -n opsramp-sdn --ignore-not-found"
                self.framework.run_command(cleanup_cmd)      
        
        # Create Traffic Director CR
        logger.info("Creating Traffic Director CR with VIP 169.254.1.5")
        
        td_cr_yaml = """
apiVersion: gateway.sdn.opsramp.com/v1
kind: TrafficDirector
metadata:
  name: td-all-gateways
  namespace: opsramp-sdn
spec:
  gateways:
    - namespace: ns1
      vip: "169.254.1.5"
    - namespace: ns2
      vip: "169.254.1.5"
    - namespace: ns3
      vip: "169.254.1.5"
    - namespace: ns4
      vip: "169.254.1.5"
"""
        
        # Write CR to temporary file and apply
        cr_file = "/tmp/td-cr.yaml"
        with open(cr_file, 'w') as f:
            f.write(td_cr_yaml)
        
        apply_cmd = f"kubectl apply -f {cr_file}"
        result = self.framework.run_command(apply_cmd)
        assert result['success'], f"Failed to create Traffic Director CR. Error: {result['stderr']}"
        
        logger.info("✓ Traffic Director CR created successfully")
        
        # Wait for Traffic Director to be ready
        logger.info("Waiting for Traffic Director to be ready...")
        time.sleep(5)  # Allow time for CR processing and route programming
        
        # Define customer devices for testing
        # Add vips for each customer in the same map customer_devices

        customer_devices = {
            'c1': {
                'devices': ['c1a1', 'c1a2', 'c1b1', 'c1b2'],  # Customer 1 devices
                'vip': "169.254.1.5",
                'http_port': 18080,
                'udp_port': 9090,
                'expected_responses': ["Hello from ns1!"]
            },
            'c2': {
                'devices': ['c2a1', 'c2b1', 'c2c1'],          # Customer 2 devices
                'vip': "169.254.1.5",
                'http_port': 18080,
                'udp_port': 9090,
                'expected_responses': ["Hello from ns2!"]
            },
            'c3': {
                'devices': ['c3a1'],                          # Customer 3 devices
                'vip': "169.254.1.5",
                'http_port': 18080,
                'udp_port': 9090,
                'expected_responses': ["Hello from ns3!"]
            },
            'c4': {
                'devices': ['c4a1'],                          # Customer 4 devices
                'vip': "169.254.1.5",
                'http_port': 18080,
                'udp_port': 9090,
                'expected_responses': ["Hello from ns4!"]
            }
        }
        
        # Test connectivity from each customer device      
        connectivity_success = self.framework.connectivity_tester.test_device_to_gateway_connectivity(
            customer_devices, 
            num_requests=1, 
            timeout=15
        )
        
        assert connectivity_success, "Connectivity tests failed for some devices"
        
        # Test reverse connectivity from gateway pods to customer devices
        logger.info("Testing reverse connectivity from gateway pods to customer devices...")
        
        gateway_to_customer_mapping = {
            'ns1': {
                'devices': [
                    {'ip': '192.168.11.1', 'expected_response': 'Hello from 192.168.11.1!'},
                    {'ip': '192.168.11.2', 'expected_response': 'Hello from 192.168.11.2!'},
                    {'ip': '192.168.12.1', 'expected_response': 'Hello from 192.168.12.1!'},
                    {'ip': '192.168.12.2', 'expected_response': 'Hello from 192.168.12.2!'}
                ]
            },
            'ns2': {
                'devices': [
                    {'ip': '192.168.21.1', 'expected_response': 'Hello from 192.168.21.1!'},
                    {'ip': '192.168.22.1', 'expected_response': 'Hello from 192.168.22.1!'},
                    {'ip': '192.168.23.1', 'expected_response': 'Hello from 192.168.23.1!'}
                ]
            },
            'ns3': {
                'devices': [
                    {'ip': '192.168.31.1', 'expected_response': 'Hello from 192.168.31.1!'}
                ]
            },
            'ns4': {
                'devices': [
                    {'ip': '192.168.41.1', 'expected_response': 'Hello from 192.168.41.1!'}
                ]
            }
        }
        
        reverse_connectivity_success = self.framework.connectivity_tester.test_gateway_to_device_connectivity(
            gateway_to_customer_mapping,
            num_requests=1,
            timeout=15
        )
        
        assert reverse_connectivity_success, "Reverse connectivity tests failed for some gateway-device pairs"
        
        # Additional validation: Check Traffic Director status
        logger.info("Checking Traffic Director CR status...")
        status_cmd = "kubectl get trafficdirector td-all-gateways -n opsramp-sdn -o yaml"
        result = self.framework.run_command(status_cmd)
        assert result['success'], f"Failed to get Traffic Director status. Error: {result['stderr']}"
        
        logger.info("✓ Test 5 passed: Traffic Director CR created and all devices can connect to VIP")
        
        # Cleanup the CR
        cleanup_cmd = f"kubectl delete -f {cr_file}"
        self.framework.run_command(cleanup_cmd)
        logger.info("✓ Traffic Director CR cleaned up")

