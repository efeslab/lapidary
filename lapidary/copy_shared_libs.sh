#! /bin/bash

LIBC_PATH=$(realpath ../libc/glibc/build/install/lib)
SOS=$(ldd bin/* | grep "=>" | cut -f 2 | cut -d" " -f 3 | grep -v "/home" | sort | uniq | grep -v "libc" | grep -v "ld-linux")
for so in $SOS; do
  cp -v $so $LIBC_PATH
done
