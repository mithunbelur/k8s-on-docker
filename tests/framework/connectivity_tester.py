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
    
    def test_customer_device_connectivity(self, customer_devices: Dict, num_requests: int = 2, timeout: int = 15) -> bool:
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
                
                # Test multiple requests to verify load balancing
                responses = []
                for i in range(num_requests):
                    curl_cmd = f"docker exec {device} curl -s --connect-timeout 10 http://{customer['vip']}"
                    result = self.command_runner.run_command(curl_cmd, timeout=timeout)
                    
                    if result['success'] and result['stdout']:
                        responses.append(result['stdout'].strip())
                        logger.info(f"  Request {i+1}: {result['stdout'].strip()}")
                    else:
                        logger.warning(f"  Request {i+1}: Failed - {result['stderr']}")
                
                # Validate that we got responses
                if len(responses) == 0:
                    logger.error(f"No successful responses from device {device} to VIP {customer['vip']}")
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
