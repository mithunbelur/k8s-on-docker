#!/bin/bash

set -e

echo "Setting up test environment for the first time..."

# Install python3-full if not already installed
if ! dpkg -l | grep -q python3-full; then
    echo "Installing python3-full..."
    sudo apt update
    sudo apt install -y python3-full
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install test dependencies
echo "Installing test dependencies..."
pip install -r requirements-test.txt

# Make scripts executable
chmod +x test_framework.py run_tests.sh

echo "✓ Test environment setup complete!"
echo ""
echo "To run tests:"
echo "  ./run_tests.sh"
echo ""
echo "Or activate the virtual environment and run manually:"
echo "  source venv/bin/activate"
echo "  python3 test_framework.py"
