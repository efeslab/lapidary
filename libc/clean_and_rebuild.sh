#! /bin/bash
set -e
set -v

cd glibc
rm -rf build 
mkdir build 
cd build 
../configure CFLAGS="-g -O1" --prefix "`pwd`/install"
make -j$((`nproc`+1))
make install -j$((`nproc`+1))

cp /lib/x86_64-linux-gnu/libz.so.1 install/lib/
