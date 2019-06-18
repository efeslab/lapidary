#! /bin/bash
set -e
set -v

git clone git://sourceware.org/git/glibc.git
cd glibc
git checkout release/2.29/master
cp -r ../patch/* .
cd - #clean and rebuild.sh will reenter glibc dir

./clean_and_rebuild.sh
