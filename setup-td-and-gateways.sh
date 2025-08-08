#!/bin/bash -x

helm install trafficdirector oci://us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-charts/traffic-director --version 0.0.1 \
  --namespace opsramp-sdn --create-namespace \
  --set trafficDirectorController.programAwsRouteTable=false \
  --set trafficDirector.env.DEV_SETUP=true \
  --set trafficDirectorController.image.repository=us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-images/trafficdirector-controller \
  --set trafficDirector.image.repository=us-central1-docker.pkg.dev/opsramp-registry/gateway-cluster-images/trafficdirector \
  --set trafficDirectorController.image.tag=latest \
  --set trafficDirector.image.tag=latest

# Wait for the CRD to be created

sleep 20

helm install gw charts/target -n ns1 --create-namespace --set configmap.enabled=true --set gatewaySubnet.enabled=true --set "subnets={192.168.11.0\/24,192.168.12.0\/24}"

kubectl apply -f charts/td1.yaml