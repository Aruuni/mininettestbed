#!/bin/bash

#TODO: add the orca/sage dependencies
UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')

if [[ "$UBUNTU_VERSION" == "16.04" ]]; then
    # Execute if on Ubuntu 16.04
    echo "Detected Ubuntu 16.04 installing python3.7"
    sudo add-apt-repository -y ppa:jblgf0/python
    sudo apt update
    sudo apt install -y python3-pip openvswitch-testcontroller mininet python3.7 python3.7-dev moreutils sysstat ethtool iperf3
    sudo python3.7 -m pip install pip==20.3.4
    sudo python3.7 -m pip install  mininet numpy==1.18.5 matplotlib==3.1.3 pandas==1.0.5 tensorflow==1.14.0
else
    # Execute if on any other Ubuntu version
    sudo apt update
    sudo apt install -y python3-pip openvswitch-testcontroller mininet moreutils sysstat ethtool iperf3
    sudo python3 -m pip install mininet numpy matplotlib pandas
fi
