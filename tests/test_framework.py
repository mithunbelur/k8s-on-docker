#!/home/ubuntu/Developer/k8s-on-docker/tests/venv/bin/python3

"""
Main entry point for the Helm Test Framework.

This is a convenience script that imports and runs the modularized test framework.
"""

import sys
from framework import run_single_test, run_all_tests, print_usage

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            print_usage()
        else:
            test_name = sys.argv[1]
            run_single_test(test_name)
    else:
        run_all_tests()
