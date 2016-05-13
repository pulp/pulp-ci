#!/usr/bin/env bash
sudo sed -i "s/.slave.openstack.org//" /etc/hostname
if [ "$(which hostnamectl 2>/dev/null)" ]; then
    sudo hostnamectl set-hostname "$(cat /etc/hostname)"
fi
