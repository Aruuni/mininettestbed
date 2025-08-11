#!/bin/bash

echo "Downloading and setting up ns-3"
git clone https://gitlab.com/nsnam/ns-3-dev ~/ns-3-dev
cp ns3_simscript/CCTestBed.cc ~/ns-3-dev/scratch
cp ns3_simscript/cross_path.cc ~/ns-3-dev/scratch
cd ~/ns-3-dev
./ns3 configure --build-profile=optimized 
./ns3 

