#!/bin/bash -e


echo "Setting up for image creation..."
cp config_detector pi-gen/detector
cd pi-gen
cp -r ../stage6_detector stage6_detector
chmod +x stage6_detector/prerun.sh
chmod +x stage6_detector/00_custom/01-run.sh
chmod +x stage6_detector/00_custom/02-run-chroot.sh


echo "Building image..."
sudo CLEAN=1 ./build.sh -c config_detector
exitCode=$?
if [ $exitCode -ne 0 ]; then
    echo "Exited with code ${exitCode}" ; exit -1
fi
