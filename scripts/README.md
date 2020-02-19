Look at `common-vars.sh` for some variables that can be changed (disk name, amount of memory).

Run `install-vm.sh` to create a new VM.
- Install with the basic Ubuntu server configuration. I recommend LVM if you decide to resize the image later.

Run `extract-kernel.sh` to get the linux kernel/initrd from the install disk image. This should work for LVM qcow2 images. You'll need to install `libguestfs-tools`.

Run `run-vm.sh` every time you want to start the VM. `^a-x` to kill qemu.

Once you get the VM working, reinstall Lapidary inside the VM and do all of your gem5 work within the VM.

_I know that there are many ways to do this, but I find the raw qemu approach to work the best across a variety of setups._
