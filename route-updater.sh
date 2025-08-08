#!/bin/bash

LOG_FILE="/var/log/route-updater/route-updater.log"
NAMESPACE="opsramp-sdn"
CRD="trafficdirectors.gateway.sdn.opsramp.com"
ROUTER_NS="n1"

function setup_logging {
    if [[ ! -d "$(dirname "$LOG_FILE")" ]]; then
        mkdir -p "$(dirname "$LOG_FILE")"
    fi
    touch "$LOG_FILE"
    echo "Logging started at $(date)" >> "$LOG_FILE"
}

funtion check_and_rotate_log {
    local max_size=10485760  # 10 MB
    if [[ -f "$LOG_FILE" && $(stat -c%s "$LOG_FILE") -ge $max_size ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        touch "$LOG_FILE"
        echo "Log file rotated at $(date)" >> "$LOG_FILE"
    fi
}

# $1 is level of logging (e.g., INFO, ERROR), $2 is the message
function log {
    local level="$1"
    local message="$2"
    echo "$(date +'%Y-%m-%d %H:%M:%S') [$level] - $message" >> "$LOG_FILE"
    check_and_rotate_log
}

# Wait for the CRD to exist
log "INFO" "Waiting for CRD '$CRD' to be created..."
until kubectl get crd "$CRD" >/dev/null 2>&1; do
    sleep 5
done
log "INFO" "CRD '$CRD' found!"

# Run kubectl watch in the background and process output
kubectl get "$CRD" -n "$NAMESPACE" -o json --watch --output-watch-events | while read -r line; do
    # You can parse the line (which is JSON) using jq or grep
    # For example, trigger action when a resource is ADDED or MODIFIED
    event_type=$(echo "$line" | jq -r '.type')
    resource_name=$(echo "$line" | jq -r '.object.metadata.name')
    if [[ "$event_type" == "ADDED" || "$event_type" == "MODIFIED" ]]; then
        log "INFO" "Resource $resource_name was $event_type"
        # Place your custom action/command here, e.g.:
        # ./my-action.sh "$resource_name"
    fi
done