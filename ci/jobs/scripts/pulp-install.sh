sudo yum -y install ansible attr git libselinux-python
ssh-keygen -t rsa -N "" -f pulp_server_key
cat pulp_server_key.pub >> ~/.ssh/authorized_keys
echo 'localhost' > hosts
source "${RHN_CREDENTIALS}"
ansible-playbook --connection local -i hosts ci/ansible/pulp_server.yaml \
    -e "pulp_build=${PULP_BUILD}" \
    -e "pulp_version=${PULP_VERSION}" \
    -e "rhn_password=${RHN_PASSWORD}" \
    -e "rhn_pool=${RHN_POOL}" \
    -e "rhn_username=${RHN_USERNAME}"
