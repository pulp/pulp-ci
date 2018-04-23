#!/usr/bin/env bash
HOSTNAME="$1"
DOCKER="$(grep docker 2>/dev/null <<< ${HOSTNAME})"

echo "Disable selinux"
sudo setenforce 0

# Fail immediately on error
set -ex

source bootstrap.sh

sudo "${PKG_MGR}" install -y gcc git ansible libselinux-python

git clone https://github.com/pulp/devel.git
cd devel
git checkout 3.0-dev
sed -i -e 's/pulp_user: vagrant/pulp_user: jenkins/g' ansible/pulp-from-source.yml
echo localhost > hosts
ansible-playbook ansible/pulp-from-source.yml -i hosts --connection=local
sudo mv /home/jenkins/.bashrc /home/jenkins/bashrc