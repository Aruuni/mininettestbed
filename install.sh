#installs python from source with make altinstall, caled with python3.X
sudo apt-get update && sudo apt-get install -y build-essential libssl-dev zlib1g-dev libncurses5-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev && wget https://www.python.org/ftp/python/3.7.12/Python-3.7.12.tgz && tar -xf Python-3.7.12.tgz && cd Python-3.7.12 && ./configure --enable-optimizations && make -j $(nproc) && sudo make altinstall
sudo python3.7 install mininet numpy matplotlib pandas