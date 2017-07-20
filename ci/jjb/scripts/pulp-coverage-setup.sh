if [ "$(echo -e 2.8\\n"${PULP_VERSION}" | sort -V | head -n 1)" = "2.8" ] && [ "${OS}" != "rhel6" ]; then
    export ANSIBLE_CONFIG="${PWD}/ci/ansible/ansible.cfg"
    ansible-playbook --connection local -i hosts ci/ansible/pulp_coverage.yaml
fi
