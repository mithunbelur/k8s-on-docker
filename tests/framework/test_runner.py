"""
Test execution utilities.
"""

import pytest
from .config import is_debug_enabled

def run_single_test(test_name: str):
    """Run a single test by name."""
    # Add -s flag to disable output capture when debug is enabled
    debug_enabled = is_debug_enabled()
    if debug_enabled:
        pytest.main(["-v", "-s", f"test_traffic_director.py::{test_name}"])
    else:
        pytest.main(["-v", f"test_traffic_director.py::{test_name}"])

def run_all_tests():
    """Run all tests."""
    # Add -s flag to disable output capture when debug is enabled
    debug_enabled = is_debug_enabled()
    if debug_enabled:
        pytest.main(["-v", "-s", "test_traffic_director.py"])
    else:
        pytest.main(["-v", "test_traffic_director.py"])

def print_usage():
    """Print usage instructions."""
    print("""
Traffic Director Test Framework Usage:

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
   ./test_framework.py TestTrafficDirector::test_install_with_program_aws_route_table_true_no_table
   ./test_framework.py TestTrafficDirector::test_create_single_traffic_director_all_namespace_same_vip

3. Enable debug mode (prints command output to console):
   TEST_DEBUG=true ./test_framework.py
   TEST_DEBUG=1 ./test_framework.py TestTrafficDirector::test_install_with_program_aws_route_table_false

4. Set custom log file:
   TEST_LOG_FILE=/tmp/my_test.log ./test_framework.py
   TEST_LOG_FILE=/path/to/custom.log TEST_DEBUG=true ./test_framework.py

5. Using pytest directly (after activating venv):
   source venv/bin/activate
   pytest test_traffic_director.py -v
   TEST_DEBUG=true pytest test_traffic_director.py -v -s

6. Using the run script:
   ./run_tests.sh
   TEST_DEBUG=true ./run_tests.sh

Available Test Cases:
- test_install_with_program_aws_route_table_true_no_table (Test 1): Install with programAwsRouteTable=true but no awsRouteTable
- test_install_with_program_aws_route_table_true_no_irsa (Test 2): Install with programAwsRouteTable=true and dummy awsRouteTable but no awsIrsaArn
- test_install_with_program_aws_route_table_false (Test 3): Install with programAwsRouteTable=false (should succeed)
- test_install_gateway_releases (Test 4): Install 4 gateway helm releases in different namespaces
- test_create_single_traffic_director_all_namespace_same_vip (Test 5): Create Traffic Director CR and validate connectivity from customer devices
- test_create_single_traffic_director_all_namespace_different_vip (Test 6): Create Traffic Director CR with different VIPs for each namespace
- test_multiple_traffic_director_one_per_gateway (Test 7): Create multiple Traffic Director CRs, one per gateway namespace
- test_multiple_traffic_director_one_per_gateway_with_pod_restarts (Test 8): Create multiple Traffic Director CRs with Traffic Director pod restarts
- test_multiple_traffic_director_same_namespace_should_fail (Test 9): Create multiple Traffic Director CRs with same namespace should fail
- test_multiple_traffic_director_same_vip_should_fail (Test 10): Create multiple Traffic Director CRs with same VIP should fail
- test_traffic_director_update_vip (Test 11): Update Traffic Director CR with different VIPs for each namespace

Environment Variables:
- TEST_DEBUG: Set to 'true' or '1' to enable console output of all commands and detailed debugging
- TEST_LOG_FILE: Set custom log file path (default: test_traffic_director_YYYYMMDD_HHMMSS.log)

Examples:
  # Run all tests with debug output and custom log file
  TEST_DEBUG=true TEST_LOG_FILE=/tmp/td_test.log ./test_framework.py
  
  # Run specific connectivity test
  ./test_framework.py TestTrafficDirector::test_create_single_traffic_director_all_namespace_same_vip
  
  # Run validation tests only
  ./test_framework.py TestTrafficDirector::test_multiple_traffic_director_same_namespace_should_fail
  ./test_framework.py TestTrafficDirector::test_multiple_traffic_director_same_vip_should_fail

Notes:
- Tests 1-3 focus on Helm chart validation and installation
- Tests 4-8 focus on functionality and connectivity testing
- Tests 9-10 focus on admission webhook validation
- Test 11 focuses on Traffic Director CR updates
- Route-updater.py runs automatically in background during tests
- Debug mode shows command execution, return codes, stdout, and stderr
    """)
