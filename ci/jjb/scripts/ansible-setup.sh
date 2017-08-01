sudo yum -y install ansible attr git libselinux-python
source "${RHN_CREDENTIALS}"
export ANSIBLE_CONFIG="${PWD}/ci/ansible/ansible.cfg"
