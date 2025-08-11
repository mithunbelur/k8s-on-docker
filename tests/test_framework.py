#!/home/ubuntu/Developer/k8s-on-docker/tests/venv/bin/python3

"""
Helm Test Framework for TrafficDirector Installation

Setup (First time only):
1. Create virtual environment:
   python3 -m venv venv
   
2. Activate and install dependencies:
   source venv/bin/activate
   pip install -r requirements-test.txt

Usage Examples:
1. Run all tests:
   ./test_framework.py

2. Run specific test:
   ./test_framework.py TestHelmInstallation::test_install_with_aws_route_table_false

3. Using pytest directly (after activating venv):
   source venv/bin/activate
   pytest test_framework.py -v

4. Using the run script:
   ./run_tests.sh

Prerequisites:
- kubectl configured and connected to cluster
- helm installed
- python3-full installed (sudo apt install python3-full)
"""

import pytest
import subprocess
import time
import json
import os
import logging
import sys
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HelmTestFramework:
    """Test framework for Helm chart installations"""
    
    def __init__(self, debug: bool = False, log_file: str = None):
        self.namespace = "opsramp-sdn"
        self.chart_name = "trafficdirector"
        self.chart_url = "oci://us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-charts/traffic-director"
        self.chart_version = "0.0.1"
        self.debug = debug
        
        # Setup file logging if log_file is specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")

    def debug_print(self, message: str):
        """Print debug message to stdout only"""
        if self.debug:
            print(message, flush=True)
        
    def run_command(self, cmd: str, capture_output: bool = True, timeout: int = 60) -> Dict:
        """Run a shell command and return result"""
        try:
            logger.info(f"Executing: {cmd}")
            
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            
            command_result = {
                'returncode': result.returncode,
                'stdout': result.stdout.strip() if result.stdout else "",
                'stderr': result.stderr.strip() if result.stderr else "",
                'success': result.returncode == 0
            }
            
            # Print debug output if enabled
            if self.debug:
                self.debug_print(f"\n[DEBUG] Command: {cmd}")
                self.debug_print(f"[DEBUG] Return code: {command_result['returncode']}")
                if command_result['stdout']:
                    self.debug_print(f"[DEBUG] STDOUT:\n{command_result['stdout']}")
                if command_result['stderr']:
                    self.debug_print(f"[DEBUG] STDERR:\n{command_result['stderr']}")
                self.debug_print(f"[DEBUG] Success: {command_result['success']}\n")
            
            return command_result
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out: {cmd}"
            logger.error(error_msg)
            self.debug_print(f"\n[DEBUG] {error_msg}\n")
            return {
                'returncode': -1,
                'stdout': "",
                'stderr': "Command timed out",
                'success': False
            }
        except Exception as e:
            error_msg = f"Command failed: {cmd}, Error: {e}"
            logger.error(error_msg)
            self.debug_print(f"\n[DEBUG] {error_msg}\n")
            return {
                'returncode': -1,
                'stdout': "",
                'stderr': str(e),
                'success': False
            }
    
    def cleanup_helm_release(self, release_name: str = None) -> bool:
        """Clean up helm release"""
        if release_name is None:
            release_name = self.chart_name
            
        cmd = f"helm uninstall {release_name} -n {self.namespace} --ignore-not-found"
        result = self.run_command(cmd)
        
        # Wait for cleanup
        time.sleep(5)
        return result['success']
    
    def helm_install(self, extra_args: str = "") -> Dict:
        """Install helm chart with optional extra arguments"""
        base_cmd = (
            f"helm install {self.chart_name} {self.chart_url} "
            f"--version {self.chart_version} "
            f"--namespace {self.namespace} --create-namespace "
            f"--set trafficDirectorController.image.repository=us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-images/trafficdirector-controller "
            f"--set trafficDirector.image.repository=us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-images/trafficdirector "
            f"--set trafficDirectorController.image.tag=latest "
            f"--set trafficDirector.image.tag=latest"
        )
        
        if extra_args:
            cmd = f"{base_cmd} {extra_args}"
        else:
            cmd = base_cmd
            
        return self.run_command(cmd)
    
    def check_pods_status(self, namespace: str, timeout: int = 60) -> Dict:
        """Check if pods are running in the namespace"""
        cmd = f"kubectl get pods -n {namespace} -o json"
        result = self.run_command(cmd)
        
        if not result['success']:
            return {'success': False, 'message': 'Failed to get pods'}
        
        try:
            pods_data = json.loads(result['stdout'])
            pods = pods_data.get('items', [])
            
            if not pods:
                return {'success': False, 'message': 'No pods found'}
            
            running_pods = 0
            total_pods = len(pods)
            
            for pod in pods:
                status = pod.get('status', {})
                phase = status.get('phase', '')
                if phase == 'Running':
                    running_pods += 1
            
            return {
                'success': running_pods == total_pods,
                'message': f"{running_pods}/{total_pods} pods running",
                'running_pods': running_pods,
                'total_pods': total_pods
            }
            
        except json.JSONDecodeError as e:
            return {'success': False, 'message': f'Failed to parse pods JSON: {e}'}
    
    def wait_for_pods_ready(self, namespace: str, timeout: int = 120) -> bool:
        """Wait for all pods to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_pods_status(namespace)
            if status['success']:
                logger.info(f"All pods are running: {status['message']}")
                return True
            
            logger.info(f"Waiting for pods... {status['message']}")
            time.sleep(10)
        
        logger.error(f"Timeout waiting for pods to be ready in {namespace}")
        return False

# Test class
class TestHelmInstallation:
    """Test cases for Helm installation scenarios"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Check for debug flag from environment variable or command line
        debug_enabled = os.environ.get('TEST_DEBUG', '').lower() in ['true', '1', 'yes']
        log_file = os.environ.get('TEST_LOG_FILE')  # Optional log file
        self.framework = HelmTestFramework(debug=debug_enabled, log_file=log_file)
        
        # Cleanup before test
        self.framework.cleanup_helm_release()
        
        yield
        
        # Cleanup after test
        self.framework.cleanup_helm_release()
    
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

# Utility functions for running tests
def run_single_test(test_name: str):
    """Run a single test by name"""
    # Add -s flag to disable output capture when debug is enabled
    debug_enabled = os.environ.get('TEST_DEBUG', '').lower() in ['true', '1', 'yes']
    if debug_enabled:
        pytest.main(["-v", "-s", f"{__file__}::{test_name}"])
    else:
        pytest.main(["-v", f"{__file__}::{test_name}"])

def run_all_tests():
    """Run all tests"""
    # Add -s flag to disable output capture when debug is enabled
    debug_enabled = os.environ.get('TEST_DEBUG', '').lower() in ['true', '1', 'yes']
    if debug_enabled:
        pytest.main(["-v", "-s", __file__])
    else:
        pytest.main(["-v", __file__])

def print_usage():
    """Print usage instructions"""
    print("""
Helm Test Framework Usage:

Setup (First time only):
1. Create virtual environment:
   python3 -m venv venv
   
2. Activate and install dependencies:
   source venv/bin/activate
   pip install -r requirements-test.txt

Usage:
1. Run all tests:
   ./test_framework.py

2. Run specific test:
   ./test_framework.py TestHelmInstallation::test_install_with_aws_route_table_false
   ./test_framework.py TestHelmInstallation::test_install_with_aws_route_table_true_no_table
   ./test_framework.py TestHelmInstallation::test_install_with_aws_route_table_true_no_irsa

3. Enable debug mode (prints command output to console):
   TEST_DEBUG=true ./test_framework.py
   TEST_DEBUG=1 ./test_framework.py TestHelmInstallation::test_install_with_aws_route_table_false

4. Using pytest directly (after activating venv):
   source venv/bin/activate
   pytest test_framework.py -v
   TEST_DEBUG=true pytest test_framework.py -v -s

5. Using the run script:
   ./run_tests.sh
   TEST_DEBUG=true ./run_tests.sh

Available Tests:
- test_install_with_aws_route_table_true_no_table: Test AWS route table validation
- test_install_with_aws_route_table_true_no_irsa: Test AWS IRSA validation  
- test_install_with_aws_route_table_false: Test successful installation

Debug Options:
- Set TEST_DEBUG=true to enable console output of all commands
- Debug mode shows command execution, return codes, stdout, and stderr
    """)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            print_usage()
        else:
            test_name = sys.argv[1]
            run_single_test(test_name)
    else:
        run_all_tests()
