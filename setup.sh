sudo fuser -k 6653/tcp
sudo modprobe tcp_bbr
UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')

# if you nee to use secure boot, you must sign theese, like this 
# sudo /lib/modules/$(uname -r)/build/scripts/sign-file sha256 ~/bbr/mok.key ~/bbr/mok.pem CC/PCC-Kernel/src/tcp_pcc.ko
sudo insmod CC/PCC-Kernel/src/tcp_pcc.ko 2> /dev/null
sudo insmod CC/astraea-open-source/kernel/tcp-astraea/tcp_astraea.ko 2> /dev/null
sudo insmod CC/sage/cc-module/tcp_sage.ko 2> /dev/null

#Orca settigns
sudo sysctl -w net.ipv4.tcp_low_latency=1 > /dev/null
sudo sysctl -w net.ipv4.tcp_autocorking=0 > /dev/null
sudo sysctl -w net.ipv4.tcp_no_metrics_save=1 > /dev/null