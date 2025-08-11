"""
Configuration module for the test framework.
"""

import os

# Default configuration
DEFAULT_NAMESPACE = "opsramp-sdn"
DEFAULT_CHART_NAME = "trafficdirector"
DEFAULT_CHART_URL = "oci://us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-charts/traffic-director"
DEFAULT_CHART_VERSION = "0.0.1"

# Gateway configurations
GATEWAY_CONFIGS = [
    {
        'namespace': 'ns1',
        'subnets': '192.168.11.0/24,192.168.12.0/24'
    },
    {
        'namespace': 'ns2', 
        'subnets': '192.168.21.0/24'
    },
    {
        'namespace': 'ns3',
        'subnets': '192.168.31.0/24'
    },
    {
        'namespace': 'ns4',
        'subnets': '192.168.41.0/24'
    }
]

# Environment variable checks
def is_debug_enabled() -> bool:
    """Check if debug mode is enabled via environment variables."""
    return os.environ.get('TEST_DEBUG', '').lower() in ['true', '1', 'yes']

def get_log_file() -> str:
    """Get log file path from environment variables."""
    return os.environ.get('TEST_LOG_FILE')
