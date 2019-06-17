#! /bin/bash

sudo apt install -y python3 python-pip python3-pip make scons gcc gdb g++ \
  gfortran cmake python-tk patchelf

sudo -H pip install -r requirements.txt
sudo -H pip3 install -r requirements.txt
