#!/bin/bash -x

ROLE=$1
#Role can be either 'control-plane' or 'worker-node'
if [ "$ROLE" != "control-plane" ] && [ "$ROLE" != "worker-node" ]; then
  echo "Usage: $0 <control-plane|worker-node>"
  exit 1
fi

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

systemctl enable --now crio

kubeadm config images pull

systemctl enable --now kubelet

# If the role is control-plane, initialize the cluster
if [ "$ROLE" == "control-plane" ]; then
    echo "Initializing Kubernetes control plane..."
    kubeadm init --apiserver-advertise-address=10.10.10.10 --pod-network-cidr=10.244.0.0/16 > kubeadm-init.log 2>&1

    mkdir -p $HOME/.kube
    cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
    chown $(id -u):$(id -g) $HOME/.kube/config
    chmod 644 /etc/kubernetes/admin.conf

    sleep 10

    kubectl apply -f https://github.com/coreos/flannel/raw/master/Documentation/kube-flannel.yml

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

