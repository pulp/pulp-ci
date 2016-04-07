#!/bin/bash
set -ex

# Collect some facts
export DISTRIBUTION=$(python -c "import platform, sys
sys.stdout.write(platform.dist()[0])")
export DISTRIBUTION_MAJOR_VERSION=$(python -c "import platform, sys
sys.stdout.write(platform.dist()[1].split('.')[0])")
export PKG_MGR=$(which dnf 2>/dev/null || which yum 2>/dev/null)

# Create the jenkins user in the jenkins group
sudo useradd --user-group --create-home --home-dir /home/jenkins jenkins
sudo cp jenkins-sudoers "/etc/sudoers.d/00-jenkins"
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
