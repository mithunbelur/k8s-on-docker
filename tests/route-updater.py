#!/usr/bin/env python3

import os
import json
import time
import logging
import sys
from logging.handlers import RotatingFileHandler

# Add debug output immediately
print("Route updater starting...", flush=True)

try:
    from kubernetes import client, config, watch
    from kubernetes.client.rest import ApiException
    print("Kubernetes imports successful", flush=True)
except ImportError as e:
    print(f"Failed to import kubernetes: {e}", flush=True)
    sys.exit(1)

# Configuration
LOG_FILE = "/var/log/route-updater/route-updater.log"
NAMESPACE = "opsramp-sdn"
CRD_GROUP = "gateway.sdn.opsramp.com"
CRD_VERSION = "v1"
CRD_PLURAL = "trafficdirectors"
ROUTER_NS = "n1"
EGRESS_INTERFACE = "lana_1"

# Global map to store VIPs by TrafficDirector name
traffic_director_vips = {}

def setup_logging():
    """Setup logging with rotation"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('route-updater')
    logger.setLevel(logging.INFO)
    
    # Create rotating file handler (10MB max, 1 backup)
    handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=1
    )
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

def wait_for_crd(api_client, logger):
    """Wait for the CRD to exist"""
    logger.info(f"Waiting for CRD '{CRD_PLURAL}.{CRD_GROUP}' to be created...")
    
    while True:
        try:
            api_client.read_custom_resource_definition(f"{CRD_PLURAL}.{CRD_GROUP}")
            logger.info(f"CRD '{CRD_PLURAL}.{CRD_GROUP}' found!")
            break
        except ApiException as e:
            if e.status == 404:
                time.sleep(5)
                continue
            else:
                logger.error(f"Error checking for CRD: {e}")
                raise

def process_event(event, logger):
    """Process a watch event"""
    event_type = event['type']
    namespace = event['object']['metadata']['namespace']
    td_name = f"{namespace}/{event['object']['metadata']['name']}"
    
    if event_type in ['ADDED', 'MODIFIED']:
        logger.info(f"Resource {td_name} was {event_type}")
        # Extract the spec from the resource for route updates
        call_custom_action(td_name, event['object'], logger)
    
    if event_type == 'DELETED':
        logger.info(f"Resource {td_name} was deleted")
        # Clean up routes for deleted TrafficDirector
        delete_routes_for_vips(td_name, logger)

def call_custom_action(td_name, resource_obj, logger):
    """Custom action to perform when resource changes"""
    try:
        # First clean up any existing routes for this TrafficDirector
        delete_routes_for_vips(td_name, logger)
        # Extract traffic director spec
        spec = resource_obj.get('spec', {})
        status = resource_obj.get('status', {})
        logger.info(f"Processing TrafficDirector {td_name} with spec: {json.dumps(spec, indent=2)}")
        
        # Extract nodeIp from status
        node_ip = status.get('nodeIp')
        if not node_ip:
            logger.warning(f"No nodeIp found in status for TrafficDirector {td_name}")
            return
            
        # Extract VIPs from gateways
        gateways = spec.get('gateways', [])
        vips = []
        
        for gateway in gateways:
            namespace = gateway.get('namespace')
            vip = gateway.get('vip')
            if vip:
                vips.append({
                    'namespace': namespace,
                    'vip': vip,
                    'nodeIp': node_ip
                })
                logger.info(f"Found VIP {vip} for namespace {namespace} with nodeIp {node_ip}")
        
        # Store VIPs in the global map
        traffic_director_vips[td_name] = vips
        logger.info(f"Stored {len(vips)} VIPs for TrafficDirector {td_name}")
        
        # Log current state of all VIPs
        logger.info(f"Current VIP map: {json.dumps(traffic_director_vips, indent=2)}")
        
        # Update routes in network namespaces based on VIPs
        update_routes_for_vips(td_name, vips, logger)
        
    except Exception as e:
        logger.error(f"Error in custom action for {td_name}: {e}")

def update_routes_for_vips(td_name, vips, logger):
    """Update network routes based on VIPs"""
    try:
        for vip_config in vips:
            vip = vip_config['vip']
            namespace = vip_config['namespace']
            node_ip = vip_config['nodeIp']
            
            # Execute route add command
            cmd = f"ip netns exec {ROUTER_NS} ip route add {vip}/32 via {node_ip} dev {EGRESS_INTERFACE}"
            logger.info(f"Executing: {cmd}")
            
            result = os.system(cmd)
            if result == 0:
                logger.info(f"Successfully added route for VIP {vip} via {node_ip}")
            else:
                logger.error(f"Failed to add route for VIP {vip} via {node_ip} (exit code: {result})")
            
    except Exception as e:
        logger.error(f"Error updating routes for {td_name}: {e}")

def delete_routes_for_vips(td_name, logger):
    """Delete network routes for a TrafficDirector"""
    try:
        if td_name in traffic_director_vips:
            vips = traffic_director_vips[td_name]
            for vip_config in vips:
                vip = vip_config['vip']
                namespace = vip_config['namespace']
                node_ip = vip_config['nodeIp']
                
                # Execute route delete command
                cmd = f"ip netns exec {ROUTER_NS} ip route del {vip}/32 via {node_ip} dev {EGRESS_INTERFACE}"
                logger.info(f"Executing: {cmd}")
                
                result = os.system(cmd)
                if result == 0:
                    logger.info(f"Successfully deleted route for VIP {vip} via {node_ip}")
                else:
                    logger.error(f"Failed to delete route for VIP {vip} via {node_ip} (exit code: {result})")
                
            del traffic_director_vips[td_name]
            logger.info(f"Deleted routes for TrafficDirector {td_name}")
        else:
            logger.warning(f"No VIPs found for TrafficDirector {td_name}")
    except Exception as e:
        logger.error(f"Error deleting routes for {td_name}: {e}")

def main():
    """Main function"""
    print("Entering main function", flush=True)
    logger = setup_logging()
    logger.info("Route updater started")
    print("Logger setup complete", flush=True)
    
    try:
        # Load kubernetes config
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded local kube config")
        
        # Create API clients
        api_extensions = client.ApiextensionsV1Api()
        custom_api = client.CustomObjectsApi()
        
        # Wait for CRD to exist
        wait_for_crd(api_extensions, logger)
        
        # Watch for changes
        logger.info(f"Starting watch on {CRD_PLURAL} in namespace {NAMESPACE}")
        
        w = watch.Watch()
        for event in w.stream(
            custom_api.list_namespaced_custom_object,
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL
        ):
            try:
                process_event(event, logger)
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                continue
                
    except KeyboardInterrupt:
        logger.info("Route updater stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
