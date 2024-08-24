#installs python from source with make altinstall, caled with python3.X
#sudo apt-get update && sudo apt-get install -y build-essential moreutils libssl-dev zlib1g-dev libncurses5-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev && wget https://www.python.org/ftp/python/3.7.12/Python-3.7.12.tgz && tar -xf Python-3.7.12.tgz && cd Python-3.7.12 && ./configure --enable-optimizations && make -j $(nproc) && sudo make altinstall
sudo add-apt-repository -y ppa:jblgf0/python
sudo apt update
sudo apt install -y pyhton3.5-dev python3.7 python3.7-dev python3-pip openvswitch-testcontroller mininet moreutils sysstat
sudo python3 -m pip install -y mininet numpy matplotlib pandas #--break-system-packages
