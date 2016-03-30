#!/usr/bin/env bash
HOSTNAME="$1"
VANILLA="$(grep vanilla 2>/dev/null <<< ${HOSTNAME})"
DOCKER="$(grep docker 2>/dev/null <<< ${HOSTNAME})"

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
    cat > mrg.repo <<EOF
[mrg-el5]
name=mrg-el5
baseurl=http://download.devel.redhat.com/cds/prod/content/dist/rhel/server/5/5Server/x86_64/mrg-m/2/os/
enabled=1
gpgcheck=0
EOF
    sudo mv mrg.repo /etc/yum.repos.d/
elif  [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "6" ]; then
    sudo rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm
    sudo rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-6.noarch.rpm
elif  [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "7" ]; then
    sudo rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
    sudo rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-7.noarch.rpm
elif  [ "$OS_NAME" == "Fedora" ]; then
    sudo sed -i 's/clean_requirements_on_remove=true/clean_requirements_on_remove=false/g' /etc/dnf/dnf.conf
    sudo dnf install -y python-dnf
fi

sudo yum install -y puppet

echo "Installing packaging repository"
git clone https://github.com/pulp/pulp_packaging.git

echo "Installing required puppet modules"
sudo puppet module install --verbose --force puppetlabs-stdlib
sudo puppet module install --verbose --force saz-sudo

if [ ! "${VANILLA}" ] && [ ! "${DOCKER}" ]; then
    sudo puppet module install --verbose --force puppetlabs-mongodb
    sudo puppet module install --verbose --force ripienaar-module_data
    sudo puppet module install --verbose --force katello-qpid

    echo "Configuring pulp-unittest"
    sudo puppet apply pulp_packaging/ci/deploy/utils/puppet/pulp-unittest.pp
fi

echo "Disable ttysudo requirement"
sudo sed -i 's|Defaults[ ]*requiretty|#Defaults    requiretty|g' /etc/sudoers

echo "Configuring jenkins_node_setup user"
sudo puppet apply pulp_packaging/ci/deploy/utils/puppet/jenkins_node_setup.pp

if [ "$OS_NAME" == "RedHatEnterpriseServer" ] && [ "$OS_VERSION" == "6" ] && [ ! "${DOCKER}" ]; then
    sudo rm -f /etc/udev/rules.d/70*
    sudo sed -i '/^\(HWADDR)\|UUID\)=/d' /etc/sysconfig/network-scripts/ifcfg-eth0
fi

if [ "${DOCKER}" ]; then
    sudo yum install -y docker
    sudo systemctl enable docker

    echo "Allowing jenkins user access to docker"
    sudo groupadd docker
    sudo gpasswd -a jenkins docker
    # add -G docker to docker's OPTIONS in /etc/sysconfig/docker
    sudo sed -i "s/^\(OPTIONS=.*\)'/\1 -G docker'/" /etc/sysconfig/docker
fi
