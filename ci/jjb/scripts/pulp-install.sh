sudo yum -y install ansible attr git libselinux-python
echo 'localhost' > hosts
source "${RHN_CREDENTIALS}"
export ANSIBLE_CONFIG="${PWD}/ci/ansible/ansible.cfg"
ansible-playbook --connection local -i hosts ci/ansible/pulp_server.yaml \
    -e "pulp_build=${PULP_BUILD}" \
    -e "pulp_version=${PULP_VERSION}" \
    -e "rhn_password=${RHN_PASSWORD}" \
    -e "rhn_pool=${RHN_POOL}" \
    -e "rhn_username=${RHN_USERNAME}"
