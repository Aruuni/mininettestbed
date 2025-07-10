sudo fuser -k 6653/tcp
sudo modprobe tcp_bbr
UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')

# if you need to use secure boot, you must sign theese, like this 
# sudo /lib/modules/$(uname -r)/build/scripts/sign-file sha256 ~/bbr/mok.key ~/bbr/mok.pem CC/PCC-Kernel/src/tcp_pcc.ko
sudo insmod CC/PCC-Kernel/src/tcp_pcc.ko 2> /dev/null
sudo insmod CC/astraea-open-source/kernel/tcp-astraea/tcp_astraea.ko 2> /dev/null

#Orca settigns
sudo sysctl -w net.ipv4.tcp_low_latency=1
sudo sysctl -w net.ipv4.tcp_autocorking=0
sudo sysctl -w net.ipv4.tcp_no_metrics_save=1

#MPTCP out-of-tree kernel settings
sudo sysctl -w net.ipv4.tcp_allowed_congestion_control="reno cubic bbr pcc lia olia balia wvegas"
sudo sysctl -w net.mptcp.mptcp_enabled=1
sudo sysctl -w net.mptcp.mptcp_path_manager=fullmesh