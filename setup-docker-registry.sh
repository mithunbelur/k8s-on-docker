#!/bin/bash -x

docker pull registry:2

docker kill lab-registry || true

docker rm lab-registry || true

sleep 3

mkdir -p /etc/docker
cat <<EOF | sudo tee /etc/docker/daemon.json
{
  "dns": ["8.8.8.8", "4.4.2.2"],
  "insecure-registries": ["127.0.0.1:5000"]
}
EOF

sudo systemctl restart docker

docker run --rm -d -p 5000:5000 --name lab-registry registry:2
