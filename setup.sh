sudo fuser -k 6653/tcp
sudo modprobe tcp_bbr





#Orca settigns
sudo sysctl -w net.ipv4.tcp_low_latency=1
sudo sysctl -w net.ipv4.tcp_autocorking=0
sudo sysctl -w net.ipv4.tcp_no_metrics_save=1