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
   pytest test_traffic_director.py -v
   TEST_DEBUG=true pytest test_traffic_director.py -v -s

5. Using the run script:
   ./run_tests.sh
   TEST_DEBUG=true ./run_tests.sh

Available Tests:
- test_install_with_aws_route_table_true_no_table: Test AWS route table validation
- test_install_with_aws_route_table_true_no_irsa: Test AWS IRSA validation  
- test_install_with_aws_route_table_false: Test successful installation
- test_install_gateway_releases: Test installing 4 gateway releases

Debug Options:
- Set TEST_DEBUG=true to enable console output of all commands
- Debug mode shows command execution, return codes, stdout, and stderr
    """)
