#!/bin/bash
sudo dnf -y update
sudo dnf -y install ansible git

# make a temp dir to clone all the things
tempdir="$(mktemp --directory)"
pushd "$tempdir"

git clone https://github.com/pulp/ansible-pulp.git

# get the playbook locally
curl https://raw.githubusercontent.com/PulpQE/pulp-qe-tools/master/pulp3/install_pulp3/ansible.cfg > ansible.cfg
curl https://raw.githubusercontent.com/PulpQE/pulp-qe-tools/master/pulp3/install_pulp3/source-install-plugins.yml > install.yml

echo "Installing roles."
export ANSIBLE_ROLES_PATH="./ansible-pulp/roles/"
ansible-galaxy install -r ./ansible-pulp/requirements.yml

echo "Available roles."
ansible-galaxy list

echo "Create hosts file."
echo 'localhost' > hosts
source "${RHN_CREDENTIALS}"

echo "Starting Pulp 3 Installation."
ansible-playbook --connection local -i hosts -u root install.yml -v -e pulp_pip_editable=no -e pulp_content_host="$(hostname --long):8080"

echo "Disabling Firewall service to enable access to custom content ports"
sudo systemctl disable firewalld
sudo systemctl stop firewalld
