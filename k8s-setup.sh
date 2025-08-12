#!/bin/bash -x

ROLE=$1
INTF=ex0
#Role can be either 'control-plane' or 'worker-node'
if [ "$ROLE" != "control-plane" ] && [ "$ROLE" != "worker-node" ]; then
  echo "Usage: $0 <control-plane|worker-node>"
  exit 1
fi

# Get the IP address from $INTF interface
EX0_IP=$(ip addr show $INTF | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
echo "Using IP $EX0_IP from $INTF interface for this node"

#Create k8s.conf
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1 
net.bridge.bridge-nf-call-ip6tables = 1 
net.ipv4.ip_forward                 = 1 
EOF

sysctl --system

lsmod | grep br_netfilter
lsmod | grep overlay

sysctl net.bridge.bridge-nf-call-iptables net.bridge.bridge-nf-call-ip6tables net.ipv4.ip_forward

mkdir -p /etc/containers
cat <<EOF | sudo tee -a /etc/containers/registries.conf
[[registry]]
prefix = "10.255.255.2:5000"
location = "10.255.255.2:5000"
insecure = true
EOF

systemctl enable --now crio

# Set kubelet to use ex0 IP  
echo "KUBELET_EXTRA_ARGS=--node-ip=$EX0_IP" > /etc/sysconfig/kubelet

systemctl daemon-reload
kubeadm config images pull

systemctl enable --now kubelet

 If the role is control-plane, initialize the cluster
if [ "$ROLE" == "control-plane" ]; then

    echo "kubeadm reset and cleanup"

    kubeadm reset -f
    rm -rf /etc/cni/net.d/*
    ip link delete cni0
    ip link delete flannel.1

    echo "Initializing Kubernetes control plane..."
    kubeadm init --apiserver-advertise-address=$EX0_IP --pod-network-cidr=10.244.0.0/16 > kubeadm-init.log 2>&1

    mkdir -p $HOME/.kube
    cp /etc/kubernetes/admin.conf $HOME/.kube/config
    chown $(id -u):$(id -g) $HOME/.kube/config
    chmod 644 /etc/kubernetes/admin.conf

    sleep 10

    kubectl taint nodes --all node-role.kubernetes.io/control-plane-

    #kubectl apply -f https://github.com/coreos/flannel/raw/master/Documentation/kube-flannel.yml
    # Needs manual creation of namespace to avoid helm error
    kubectl create ns kube-flannel
    kubectl label --overwrite ns kube-flannel pod-security.kubernetes.io/enforce=privileged

    helm repo add flannel https://flannel-io.github.io/flannel/
    helm install flannel --set podCidr="10.244.0.0/16" --namespace kube-flannel flannel/flannel

    #kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

    kubeadm token create --print-join-command > /root/join-command.sh
    chmod +x /root/join-command.sh
else
    echo "Joining worker node to the cluster..."
    if [ ! -f /root/join-command.sh ]; then
        echo "Join command not found. Please run the control-plane setup first."
        exit 1
    fi
    bash /root/join-command.sh
fi
