#!/usr/bin/env bash
sudo dnf -y update
sudo dnf -y install ansible git sed

# make a temp dir to clone all the things
tempdir="$(mktemp --directory)"
pushd "${tempdir}"

git clone https://github.com/pulp/ansible-pulp3.git

# get the playbook locally
curl https://raw.githubusercontent.com/PulpQE/pulp-qe-tools/master/pulp3/install_pulp3/ansible.cfg > ansible.cfg
curl https://raw.githubusercontent.com/PulpQE/pulp-qe-tools/master/pulp3/install_pulp3/source-install-plugins.yml > install.yml

sed -i -e "s/- name: Install pulpcore package from source/- name: Upgrade pip\n      pip:\n        name: pip\n        state: latest\n        virtualenv_command: '{{ pulp_python_interpreter }} -m venv'\n        virtualenv: '{{pulp_install_dir}}'\n\n    - name: Install pulpcore package from source/g" ./ansible-pulp3/roles/pulp3/tasks/install.yml

echo "Installing roles."
export ANSIBLE_ROLES_PATH="./ansible-pulp3/roles/"
ansible-galaxy install -r ./ansible-pulp3/requirements.yml

echo "Available roles."
ansible-galaxy list

echo "Create hosts file."
echo $HOSTNAME > hosts

echo "Starting Pulp 3 Installation."
ansible-playbook --connection local -i hosts -u root install.yml -v -e pulp_pip_editable=no
