sudo dnf -y update
sudo dnf -y install ansible attr git libselinux-python
echo 'localhost' > hosts
export ANSIBLE_CONFIG="${PWD}/ci/ansible/ansible.cfg"
ansible-playbook --connection local -i hosts ci/ansible/pulp_server.yaml \
    -e "pulp_build=${PULP_BUILD}" \
    -e "pulp_version=${PULP_VERSION}" \
    -e "ansible_python_interpreter=/usr/bin/python3"
