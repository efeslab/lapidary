#! /usr/bin/sudo /bin/bash
set -e

source common-vars.sh

exec qemu-system-x86_64 \
          -kernel $VM_DIR/vmlinuz-* \
          -initrd $VM_DIR/initrd.img-* \
          -nographic \
          -enable-kvm \
          -hda $IMG_NAME \
          -m $MEM \
          --append "console=ttyS0,115200n8, root=/dev/sda1" \
          -balloon virtio \
          -smp $(nproc) \
          -cpu host,$CPU_FEATURES_DISABLE \
          -net user,hostfwd=tcp::5000-:22 \
          -net nic 
