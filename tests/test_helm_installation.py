#!/home/ubuntu/Developer/k8s-on-docker/tests/venv/bin/python3

"""
Helm Installation Test Cases

This module contains test cases for Helm chart installations.
"""

import pytest
import time
import logging

from framework import HelmTestFramework
from framework.config import is_debug_enabled, get_log_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestHelmInstallation:
    """Test cases for Helm installation scenarios"""
    
    @pytest.fixture(scope='class', autouse=True)
    def setup_and_teardown(self, request):
        """Setup and teardown for the entire test suite"""
        debug_enabled = is_debug_enabled()
        log_file = get_log_file()
        # Set framework on the class itself
        request.cls.framework = HelmTestFramework(debug=debug_enabled, log_file=log_file)
        
        # Cleanup before all tests
        request.cls.framework.cleanup_helm_release()
        request.cls.framework.cleanup_gateway_releases()
        
        yield
        
        # Cleanup after all tests
        request.cls.framework.cleanup_helm_release()
        request.cls.framework.cleanup_gateway_releases()
    
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
        time.sleep(30)
        
        # Check each namespace for pod readiness
        for gateway in self.framework.gateways:
            namespace = gateway['namespace']
            logger.info(f"Checking pods in namespace {namespace}...")
            
            pods_ready = self.framework.wait_for_pods_ready(namespace, timeout=90)
            assert pods_ready, f"Pods should be running in namespace {namespace}"
            
            logger.info(f"✓ All pods ready in {namespace}")
        
        logger.info("✓ Test 4 passed: All 4 gateway releases installed successfully")
