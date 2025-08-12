"""
Connectivity testing utilities for the test framework.
"""

from typing import Dict, List
from .logger import get_logger

logger = get_logger()

class ConnectivityTester:
    """Utility class for testing connectivity from customer devices to VIPs."""
    
    def __init__(self, command_runner):
        self.command_runner = command_runner
    
    def test_device_to_gateway_connectivity(self, customer_devices: Dict, num_requests: int = 2, timeout: int = 15) -> bool:
        """
        Test connectivity from customer devices to their configured VIPs.
        
        Args:
            customer_devices: Dict with customer info including devices, vip, and expected_responses
            num_requests: Number of requests to test per device
            timeout: Timeout for each curl request
            
        Returns:
            bool: True if all connectivity tests pass
        """
        all_tests_passed = True
        
        for customer_name, customer in customer_devices.items():
            logger.info(f"Testing connectivity from {customer_name} devices to VIP {customer['vip']}")
            
            for device in customer['devices']:
                logger.info(f"Testing connectivity from device {device}")
                
                # Test UDP connectivity using this command kubectl exec -it -n ns1 target-dep-8569b5f576-xhcbn -c dp  -- bash -c "echo 'hello' | nc -u 192.168.11.1 9090 -w 1"
                udp_cmd = f"docker exec {device} bash -c \"echo 'hello' | nc -u {customer['vip']} {customer['udp_port']} -w 1\""
                udp_result = self.command_runner.run_command(udp_cmd, timeout=timeout)
                logger.info(f"Device to Gateway UDP result: {udp_result}")
                if udp_result['success'] and "Echo: hello" in udp_result['stdout']:
                    logger.info(f"  ✓ UDP connectivity to Gateway {customer['vip']} successful")
                else:
                    logger.warning(f"  ✗ UDP connectivity to Gateway {customer['vip']} failed: {udp_result['stderr']}")
                    all_tests_passed = False

                # Test multiple requests to verify load balancing
                responses = []
                for i in range(num_requests):
                    curl_cmd = f"docker exec {device} curl -s --connect-timeout 10 http://{customer['vip']}:{customer['http_port']}"
                    result = self.command_runner.run_command(curl_cmd, timeout=timeout)
                    
                    if result['success'] and result['stdout']:
                        responses.append(result['stdout'].strip())
                        logger.info(f"  Request {i+1}: {result['stdout'].strip()}")
                    else:
                        logger.warning(f"  Request {i+1}: Failed - {result['stderr']}")
                
                # Validate that we got responses
                if len(responses) == 0:
                    logger.error(f"No successful responses from device {device} to VIP {customer['vip']}:{customer['http_port']}")
                    all_tests_passed = False
                    continue
                
                # Validate that responses are from expected gateways
                valid_responses = [r for r in responses if r in customer['expected_responses']]
                if len(valid_responses) == 0:
                    logger.error(f"No valid responses from device {device}. Got: {responses}, Expected: {customer['expected_responses']}")
                    all_tests_passed = False
                    continue
                
                # Check for load balancing (log unique responses)
                unique_responses = set(responses)
                logger.info(f"  Device {device} received responses from {len(unique_responses)} different gateways: {unique_responses}")
                
                logger.info(f"✓ Device {device} successfully connected to VIP {customer['vip']}")
        
        return all_tests_passed
    
    def test_gateway_to_device_connectivity(self, gateway_to_customer_mapping: Dict, num_requests: int = 2, timeout: int = 15) -> bool:
        """
        Test reverse connectivity from gateway pods to customer devices.
        
        Args:
            gateway_to_customer_mapping: Dict with gateway namespace and device info
            num_requests: Number of requests to test per device
            timeout: Timeout for each request
            
        Returns:
            bool: True if all connectivity tests pass
        """
        all_tests_passed = True
        
        for namespace, gateway_info in gateway_to_customer_mapping.items():
            logger.info(f"Testing reverse connectivity from gateway namespace {namespace}")
            
            get_pod_cmd = f"kubectl get pods -n {namespace} -l app=target -o jsonpath='{{.items[0].metadata.name}}'"
            result = self.command_runner.run_command(get_pod_cmd)
            
            if not result['success'] or not result['stdout']:
                logger.error(f"Failed to get gateway pod in namespace {namespace}")
                all_tests_passed = False
                continue
                
            gateway_pod = result['stdout'].strip()
            logger.info(f"Testing from gateway pod: {gateway_pod}")
            
            for device in gateway_info['devices']:
                device_ip = device['ip']
                expected_response = device['expected_response']
                
                logger.info(f"Testing connectivity from {gateway_pod} to device {device_ip}")
                
                # Test ping connectivity first
                ping_cmd = f"kubectl exec -n {namespace} {gateway_pod} -c dp -- ping -c 1 -W 2 {device_ip}"
                ping_result = self.command_runner.run_command(ping_cmd, timeout=timeout)
                
                if ping_result['success'] and "0% packet loss" in ping_result['stdout']:
                    logger.info(f"  ✓ Ping to {device_ip} successful")
                else:
                    logger.warning(f"  ✗ Ping to {device_ip} failed: {ping_result['stderr']}")
                    all_tests_passed = False
                
                # Test UDP connectivity using this command kubectl exec -it -n ns1 target-dep-8569b5f576-xhcbn -c dp  -- bash -c "echo 'hello' | nc -u 192.168.11.1 9090 -w 1"
                udp_cmd = f"kubectl exec -n {namespace} {gateway_pod} -c dp -- bash -c \"echo 'hello' | nc -u {device_ip} 9090 -w 1\""
                udp_result = self.command_runner.run_command(udp_cmd, timeout=timeout)
                if udp_result['success'] and "Echo: hello" in udp_result['stdout']:
                    logger.info(f"  ✓ UDP connectivity to {device_ip} successful")
                else:
                    logger.warning(f"  ✗ UDP connectivity to {device_ip} failed: {udp_result['stderr']}")
                    all_tests_passed = False

                # Test HTTP connectivity
                responses = []
                for i in range(num_requests):
                    http_cmd = f"kubectl exec -n {namespace} {gateway_pod} -c dp -- curl -s --connect-timeout 10 http://{device_ip}:8080"
                    http_result = self.command_runner.run_command(http_cmd, timeout=timeout)
                    
                    if http_result['success'] and http_result['stdout']:
                        responses.append(http_result['stdout'].strip())
                        logger.info(f"  HTTP Request {i+1}: {http_result['stdout'].strip()}")
                    else:
                        logger.warning(f"  HTTP Request {i+1}: Failed - {http_result['stderr']}")
                
                # Validate HTTP responses
                if len(responses) == 0:
                    logger.error(f"No successful HTTP responses from {gateway_pod} to {device_ip}")
                    all_tests_passed = False
                    continue
                
                # Check if responses match expected
                valid_responses = [r for r in responses if expected_response in r]
                if len(valid_responses) == 0:
                    logger.error(f"No valid HTTP responses from {gateway_pod} to {device_ip}. Got: {responses}, Expected: {expected_response}")
                    all_tests_passed = False
                    continue
                
                logger.info(f"✓ Gateway pod {gateway_pod} successfully connected to device {device_ip}")
        
        return all_tests_passed
