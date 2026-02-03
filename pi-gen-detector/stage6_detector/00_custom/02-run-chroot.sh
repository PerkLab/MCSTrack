#!/bin/bash
sudo apt update
sudo apt upgrade -y

# Firewall setup
sudo ufw enable
sudo ufw allow 8001

# Python setup
cd /home/admin/MCSTrack
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --break-system-packages .[component]
deactivate

# Run startup script on boot
sudo echo "@reboot root /usr/local/bin/detector_startup >> /home/admin/mcstrack_detector.log" > /etc/cron.d/startup
