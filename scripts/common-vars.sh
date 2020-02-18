
# CPU Features

# -- These two configurations don't seem to boot.
#CPU_FEATURES_DISABLE="-avx,-avx2,-bmi1,-bmi2,-sse,-sse2,-ssse3,-sse4_1,-sse4_2"
#CPU_FEATURES_DISABLE="-avx,-avx2,-bmi1,-bmi2,-sse4_2,-sse4_1,-ssse3"
CPU_FEATURES_DISABLE="-avx2,-bmi1,-bmi2"
echo "CPU_FEATURES_DISABLE=$CPU_FEATURES_DISABLE"

UBUNTU_VERSION=18.04.4
UBUNTU_ISO=./iso/ubuntu-$UBUNTU_VERSION-server-amd64.iso
UBUNTU_URL=http://cdimage.ubuntu.com/releases/$UBUNTU_VERSION/release/ubuntu-$UBUNTU_VERSION-server-amd64.iso

NETBOOT_URL=http://archive.ubuntu.com/ubuntu/dists/bionic-updates/main/installer-amd64/current/images/netboot/ubuntu-installer/amd64

BOOT_DIR="./boot"
KERNEL=$BOOT_DIR/linux
KERNEL_URL=$NETBOOT_URL/linux
INITRD=$BOOT_DIR/initrd.gz
INITRD_URL=$NETBOOT_URL/initrd.gz

# Installation parameters

DISK_SIZE_GB=100

VM_DIR=$(realpath ~/workspace/vms)
VM_NAME=lapidary-vm
IMG_NAME=$VM_DIR/$VM_NAME.qcow2

# Runtime parameters

# -- This gives you 75% of the system memory for the VM.
MEM_FRAC=0.75
MEM=$(cat /proc/meminfo | grep MemTotal | awk '$3=="kB"{$2='$MEM_FRAC'*$2/1024;$3=""} 1' | tr -d " " | cut -d ":" -f 2 | cut -d "." -f 1)
echo "MEM=$MEM"


