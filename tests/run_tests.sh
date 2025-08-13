#!/bin/bash

set -e

echo "Setting up test environment..."

# Check if python3-full is installed
if ! dpkg -l | grep -q python3-full; then
    echo "Installing python3-full..."
    sudo apt update
    sudo apt install -y python3-full
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install test dependencies
echo "Installing test dependencies..."
pip install -r requirements-test.txt

# Make test file executable
chmod +x test_framework.py

# Check if debug mode is enabled
if [[ "${TEST_DEBUG,,}" == "true" || "${TEST_DEBUG}" == "1" ]]; then
    echo "Running tests in DEBUG mode..."
    export TEST_DEBUG=true
else
    echo "Running tests in normal mode..."
    echo "Use 'TEST_DEBUG=true ./run_tests.sh' to enable debug output"
fi

# Run all tests
echo "Running all Helm installation tests..."
python3 test_framework.py $1

echo "Tests completed!"

# Deactivate virtual environment
deactivate
