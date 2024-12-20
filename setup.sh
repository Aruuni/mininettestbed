sudo fuser -k 6653/tcp
sudo modprobe tcp_bbr
UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')
if [[ "$UBUNTU_VERSION" == "16.04" ]]; then
    sudo insmod ~/PCC-Kernel/src/tcp_pcc.ko
fi

#Orca settigns
sudo sysctl -w net.ipv4.tcp_low_latency=1
sudo sysctl -w net.ipv4.tcp_autocorking=0
sudo sysctl -w net.ipv4.tcp_no_metrics_save=1