#! /usr/bin/sudo /bin/bash
set -e

source common-vars.sh

mkdir -p boot
if [ ! -f $KERNEL ]; then
  wget $KERNEL_URL -O $KERNEL
fi
if [ ! -f $INITRD ]; then
  wget $INITRD_URL -O $INITRD
fi

mkdir -p iso
if [ ! -f $UBUNTU_ISO ]; then
  wget $UBUNTU_URL -O $UBUNTU_ISO
fi

if [ ! -f $IMG_NAME ]; then
  qemu-img create -f qcow2 $IMG_NAME $DISK_SIZE_GB"G"
fi

exec qemu-system-x86_64 \
          -kernel $KERNEL \
          -initrd $INITRD \
          -nographic \
          -enable-kvm \
          -boot d \
          -cdrom $UBUNTU_ISO \
          -hda $IMG_NAME \
          -m $MEM \
          --append "console=ttyS0,115200n8" \
          -balloon virtio \
          -smp $(nproc) \
          -cpu host,$CPU_FEATURES_DISABLE \
          -no-reboot
