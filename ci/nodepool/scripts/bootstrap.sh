#!/bin/bash
set -ex

# Collect some facts
export DISTRIBUTION=$(python -c "import platform, sys
sys.stdout.write(platform.dist()[0])")
export DISTRIBUTION_MAJOR_VERSION=$(python -c "import platform, sys
sys.stdout.write(platform.dist()[1].split('.')[0])")

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
    cat scripts/jenkins-sudoers | sudo tee -a /etc/sudoers
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
