#!/bin/bash
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')

if [[ "$UBUNTU_VERSION" == "16.04" ]]; then
    # Execute if on Ubuntu 16.04
    echo "Detected Ubuntu 16.04 installing python3.7"
    sudo add-apt-repository -y ppa:jblgf0/python
    sudo apt update
    sudo apt install -y python3-pip python3.7 python3.7-dev python3.6 python3.6-dev
    sudo python3.7 -m pip install pip==20.3.4
    sudo python3.7 -m pip install  mininet numpy==1.18.5 matplotlib==3.1.3 pandas==1.0.5 tensorflow==1.14.0
    sudo python3.7 -m pip install --ignore-installed --upgrade pexpect

else
    # Execute if on any other Ubuntu version
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3-pip python3.7 python3.7-dev python3-7-distutils
    sudo pip3 install -U virtualenv==15.2.*
    sudo python3 -m pip install mininet numpy matplotlib pandas 

fi

sudo apt install -y openvswitch-testcontroller mininet moreutils sysstat ethtool iperf3 cmake g++ g++-9 nlohmann-json3-dev software-properties-common

echo "Downloading and setting up pcc vivace kernel"
git clone https://github.com/PCCproject/PCC-Kernel -b vivace ~/PCC-Kernel
cd ~/PCC-Kernel/src && make
cp tcp_pcc.ko $CURRENT_DIR

echo "Downloading and setting up Orca"
git clone https://github.com/Aruuni/Orca ~/Orca
cd ~/Orca
bash build.sh

if [[ "$UBUNTU_VERSION" == "16.04" ]]; then
    eaco "Downloading and setting up sage"
    git clone https://github.com/Aruuni/sage ~/sage
    cd ~/sage
    bash build.sh

fi

echo "Downloading and setting up astraea"
git clone https://github.com/Aruuni/astraea-open-source --recursive ~/astraea-open-source
cd ~/astraea-open-source
python3.7 -m pip install pip --upgrade
python3.7 -m pip install protobuf==3.10.0 tensorflow==1.14.0 --upgrade
python3.7 -m pip install matplotlib==3.2
cd kernel/tcp-astraea
make
cd ~/astraea-open-source
cp tcp_astraea.ko $CURRENT_DIR
bash build.sh
