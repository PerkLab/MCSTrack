#!/bin/bash -e


echo "Setting up for image creation..."
cp config_mixer pi-gen/config_mixer
cd pi-gen
cp -r ../stage6_mixer stage6_mixer
chmod +x stage6_mixer/prerun.sh
chmod +x stage6_mixer/00_custom/01-run.sh
chmod +x stage6_mixer/00_custom/02-run-chroot.sh


echo "Building image..."
sudo CLEAN=1 ./build.sh -c config_mixer
exitCode=$?
if [ $exitCode -ne 0 ]; then
    echo "Exited with code ${exitCode}" ; exit -1
fi
