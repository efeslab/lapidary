#! /usr/bin/sudo /bin/bash
set -e

source common-vars.sh

# Borrowed from https://gist.github.com/pshchelo/6ffabbffaedc46456b39c037d16e1d8c

echo "Note: this works if you install linux with LVM"

modprobe nbd max_part=8
qemu-nbd --connect=/dev/nbd0 $IMG_NAME
mkdir -p /tmp/mnt
mount /dev/nbd0p1 /tmp/mnt

cp /tmp/mnt/boot/initrd.img-* $BOOT_DIR
cp /tmp/mnt/boot/vmlinuz-* $BOOT_DIR

umount /tmp/mnt
qemu-nbd -d /dev/nbd0
