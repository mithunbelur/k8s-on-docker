# Helm Test Framework

This directory contains a Python test framework for testing Helm chart installations, specifically for the TrafficDirector chart.

## Prerequisites

1. **kubectl** configured and connected to your cluster
2. **helm** installed
3. **Python 3.7+** with python3-full package
4. **Virtual environment** (to avoid externally-managed-environment issues)

## Quick Setup

1. Navigate to the tests directory:
   ```bash
   cd /home/ubuntu/Developer/k8s-on-docker/tests
   ```

2. Run the setup script (first time only):
   ```bash
   chmod +x setup_test_env.sh
   ./setup_test_env.sh
   ```

3. Run tests:
   ```bash
   ./run_tests.sh
   ```

## Manual Setup

If you prefer manual setup:

1. Install python3-full:
   ```bash
   sudo apt install python3-full
   ```

2. Create virtual environment:
   ```bash
   python3 -m venv venv
   ```

3. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

5. Make scripts executable:
   ```bash
   chmod +x test_framework.py run_tests.sh
   ```

## Running Tests

### Option 1: Using the run script (Recommended)
```bash
./run_tests.sh
```

### Option 2: Using virtual environment
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python3 test_framework.py

# Run specific test
python3 test_framework.py TestHelmInstallation::test_install_with_aws_route_table_false

# Using pytest directly
pytest test_framework.py -v

# Deactivate when done
deactivate
```

### Option 3: Direct execution (after setup)
```bash
# The test_framework.py script uses the venv python automatically
./test_framework.py

# Show help
./test_framework.py --help
```

## Available Tests

1. **test_install_with_aws_route_table_true_no_table**
   - Tests validation when `programAwsRouteTable=true` but no `awsRouteTable` is provided
   - Expected: Installation fails with specific error message

2. **test_install_with_aws_route_table_true_no_irsa**
   - Tests validation when `programAwsRouteTable=true` and `awsRouteTable` is provided but no `awsIrsaArn`
   - Expected: Installation fails with specific error message

3. **test_install_with_aws_route_table_false**
   - Tests successful installation when `programAwsRouteTable=false`
   - Expected: Installation succeeds and pods become ready

## Troubleshooting

1. **externally-managed-environment error**: 
   - Run `./setup_test_env.sh` to create a virtual environment
   - Always use `./run_tests.sh` or activate the venv first

2. **Permission denied**: 
   ```bash
   chmod +x setup_test_env.sh run_tests.sh test_framework.py
   ```

3. **python3-full not found**: 
   ```bash
   sudo apt update && sudo apt install python3-full
   ```

4. **kubectl/helm not found**: Ensure they are installed and in PATH

5. **Virtual environment issues**: Delete `venv` folder and run setup again:
   ```bash
   rm -rf venv
   ./setup_test_env.sh
   ```

## File Structure

```
tests/
├── test_framework.py      # Main test framework
├── run_tests.sh          # Test runner script
├── setup_test_env.sh     # Environment setup script
├── requirements-test.txt # Python dependencies
├── README.md            # This file
└── venv/               # Virtual environment (created by setup)
```
