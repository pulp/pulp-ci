#!/bin/bash
# This script is meant to be sourced, not executed directly, and shouldn't do
# anything more than determine some system basics and get the jenkins user and
# dependencies installed.
set -ex

# This file doesn't exist on el5, but we don't test on el5 anymore,
# so that's probably(?) fine. If needed, we could add special handling for el5
. /etc/os-release

if [ -z $ID ] || [ -z $VERSION_ID ]; then
   echo "ID and VERSION_ID not set in /etc/os-release"
   return 1
fi

# set DISTRIBUTION based on ID: If it's rhel or centos,
# make it the common "redhat". Otherwise, use ID directly.
# For our purposes, this means it should either be "redhat" or "fedora".
if [[ $ID == 'centos' ]] || [[ $ID == 'rhel' ]]; then
  DISTRIBUTION=redhat
else
  DISTRIBUTION="$ID"
fi

# We only care about the major version, so split on the dots
# and only take the first field (7.1 and 7 are stored as 7).
DISTRIBUTION_MAJOR_VERSION=`echo "$VERSION_ID"|cut -d . -f 1`

echo Bootstrapping jenkins for $DISTRIBUTION $DISTRIBUTION_MAJOR_VERSION

# use dnf if you can, otherwise use yum
if dnf --version; then
    PKG_MGR=dnf
else
    PKG_MGR=yum
fi
export PKG_MGR

# Create the jenkins user in the jenkins group
if  [ "${DISTRIBUTION}" == "redhat" ] && [ "${DISTRIBUTION_MAJOR_VERSION}" == "5" ]; then
    sudo useradd --create-home --home-dir /home/jenkins jenkins
    cat jenkins-sudoers | sed -e "s/^%//" | sudo tee -a /etc/sudoers
else
    sudo useradd --user-group --create-home --home-dir /home/jenkins jenkins
    sudo cp jenkins-sudoers "/etc/sudoers.d/00-jenkins"
fi
echo jenkins | sudo passwd --stdin jenkins

# Authorize Jenkins to ssh into
sudo mkdir -p /home/jenkins/.ssh
sudo cp id_rsa.pub /home/jenkins/.ssh/authorized_keys
sudo chmod 700 /home/jenkins/.ssh
sudo chmod 600 /home/jenkins/.ssh/authorized_keys
sudo chown -R jenkins:jenkins /home/jenkins/.ssh

# Setup repositories
if [ "${DISTRIBUTION}" = "redhat" ]; then
    sudo rm /etc/yum.repos.d/*
    sudo cp "rhel${DISTRIBUTION_MAJOR_VERSION}-rcm-internal.repo" \
        /etc/yum.repos.d/
fi

# Make sure Java is installed in order to become a Jenkins executor
sudo "${PKG_MGR}" install -y java
