#!/bin/bash -e


echo "Checking dependencies..."
sudo apt install -y coreutils quilt parted qemu-user-static debootstrap zerofree zip dosfstools e2fsprogs libarchive-tools libcap2-bin grep rsync xz-utils file git curl bc gpg pigz xxd arch-test bmap-tools kmod



echo "Cloning pi-gen repository..."
if [ -d "pi-gen" ]; then
    rm -r pi-gen
fi
git clone --branch arm64 https://github.com/RPI-Distro/pi-gen.git


echo "Setting up for image creation..."
cp config_base pi-gen/config_base
cd pi-gen
touch ./stage3/SKIP
touch ./stage4/SKIP
touch ./stage5/SKIP
touch ./stage4/SKIP_IMAGES
touch ./stage5/SKIP_IMAGES
chmod +x build.sh


echo "Building image..."
sudo ./build.sh -c config_base
exitCode=$?
if [ $exitCode -ne 0 ]; then
    echo "Exited with code ${exitCode}" ; exit -1
else
    touch ./stage0/SKIP
    touch ./stage1/SKIP
    touch ./stage2/SKIP
    touch ./stage2/SKIP_IMAGES
fi
