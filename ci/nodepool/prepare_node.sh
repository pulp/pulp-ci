#!/usr/bin/env bash

echo "Disable selinux"
sudo setenforce 0

# Fail immediately on error
set -e
set -x


echo "Performaing a general update"
sudo yum update -y

echo "Installing Puppet"
sudo yum install -y git
sudo yum install -y redhat-lsb

echo "Installing java as multiple versions makes this hard for puppet"
sudo yum install -y java

OS_NAME=$(lsb_release -si)
OS_VERSION=$(lsb_release -sr | cut -f1 -d.)
if [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "5" ]; then
    sudo rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-5.noarch.rpm
    cat > mrg.repo<< EndOfMessage
[mrg-el5]
name=mrg-el5
baseurl=http://download.devel.redhat.com/cds/prod/content/dist/rhel/server/5/5Server/x86_64/mrg-m/2/os/
enabled=1
gpgcheck=0
EndOfMessage
    sudo mv mrg.repo /etc/yum.repos.d/
elif  [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "6" ]; then
    sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm
    sudo rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-6.noarch.rpm
elif  [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "7" ]; then
    sudo rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-7.noarch.rpm
elif  [ "$OS_NAME" == "Fedora" ] && [ "$OS_VERSION" == "19" ]; then
    sudo rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-fedora-19.noarch.rpm
    sudo yum install -y hiera
elif  [ "$OS_NAME" == "Fedora" ] && [ "$OS_VERSION" == "22" ]; then
    sudo sed -i 's/clean_requirements_on_remove=true/clean_requirements_on_remove=false/g' /etc/dnf/dnf.conf
fi

sudo yum install -y puppet

echo "Installing packaging repository"
git clone https://github.com/pulp/pulp_packaging.git

echo "Installing required puppet modules"
sudo puppet module install --verbose --force puppetlabs-stdlib
sudo puppet module install --verbose --force puppetlabs-mongodb
sudo puppet module install --verbose --force ripienaar-module_data
sudo puppet module install --verbose --force katello-qpid
sudo puppet module install --verbose --force saz-sudo

echo "Disable ttysudo requirement"
sudo sed -i 's|Defaults[ ]*requiretty|#Defaults    requiretty|g' /etc/sudoers

echo "Configuring jenkins_node_setup user"
sudo puppet apply pulp_packaging/ci/deploy/utils/puppet/jenkins_node_setup.pp

echo "Configuring pulp-unittest"
sudo puppet apply pulp_packaging/ci/deploy/utils/puppet/pulp-unittest.pp

if  [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "6" ]; then
    echo "cleaning up rhel6"
    sudo rm -f /etc/udev/rules.d/70*
    sudo sed -i '/^\(HWADDR)\|UUID\)=/d' /etc/sysconfig/network-scripts/ifcfg-eth0
fi
