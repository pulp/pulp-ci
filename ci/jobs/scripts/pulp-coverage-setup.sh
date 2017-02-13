if [ "$(echo -e 2.8\\n"${PULP_VERSION}" | sort -V | head -n 1)" = "2.8" ] && [ "${OS}" != "rhel6" ]; then
    ansible-playbook --connection local -i hosts ci/ansible/pulp_coverage.yaml
fi
