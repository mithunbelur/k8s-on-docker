#!/bin/bash -x

#Prepare EC2 by installing necessary packages
curl -fsSL https://get.docker.com -o get-docker.sh
chmod +x get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p -m 755 /etc/apt/keyrings
sudo rm -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubectl
sudo apt-get install -y openvswitch-switch

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
rm get_helm.sh

#Build Images for containers
docker build -t localhost/kubeadm-fedora:v1.0 -f Dockerfile.fedora .
docker build -t localhost/client-device:v1.0 -f Dockerfile.ubuntu .
