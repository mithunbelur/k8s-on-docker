"""
Main Helm test framework class.
"""

import time
import json
from typing import Dict

from .config import DEFAULT_NAMESPACE, DEFAULT_CHART_NAME, DEFAULT_CHART_URL, DEFAULT_CHART_VERSION, GATEWAY_CONFIGS
from .command_runner import CommandRunner
from .logger import get_logger
from .connectivity_tester import ConnectivityTester

logger = get_logger()

class HelmTestFramework:
    """Test framework for Helm chart installations"""
    
    def __init__(self, debug: bool = False, log_file: str = None):
        self.namespace = DEFAULT_NAMESPACE
        self.chart_name = DEFAULT_CHART_NAME
        self.chart_url = DEFAULT_CHART_URL
        self.chart_version = DEFAULT_CHART_VERSION
        self.gateways = GATEWAY_CONFIGS
        
        # Initialize command runner
        self.command_runner = CommandRunner(debug=debug)
        
        # Initialize connectivity tester
        self.connectivity_tester = ConnectivityTester(self.command_runner)

    def run_command(self, cmd: str, capture_output: bool = True, timeout: int = 60) -> Dict:
        """Run a shell command and return result."""
        return self.command_runner.run_command(cmd, capture_output, timeout)
    
    def cleanup_helm_release(self, release_name: str = None, namespace: str = None) -> bool:
        """Clean up helm release."""
        if release_name is None:
            release_name = self.chart_name
        if namespace is None:
            namespace = self.namespace
            
        cmd = f"helm uninstall {release_name} -n {namespace} --ignore-not-found"
        result = self.run_command(cmd)
        
        # Wait for cleanup
        time.sleep(5)
        return result['success']
    
    def cleanup_gateway_releases(self) -> bool:
        """Clean up all gateway releases."""
        success = True
        
        for gateway in self.gateways:
            ns = gateway['namespace']
            logger.info(f"Cleaning up gateway release in namespace {ns}")
            result = self.cleanup_helm_release("gw", ns)
            if not result:
                success = False
                logger.error(f"Failed to cleanup gateway in {ns}")
        
        return success

    def helm_install(self, extra_args: str = "") -> Dict:
        """Install helm chart with optional extra arguments."""
        base_cmd = (
            f"helm install {self.chart_name} {self.chart_url} "
            f"--version {self.chart_version} "
            f"--namespace {self.namespace} --create-namespace "
            f"--set trafficDirector.env.DEV_SETUP=true "
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
        """Check if pods are running in the namespace."""
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
        """Wait for all pods to be ready."""
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
