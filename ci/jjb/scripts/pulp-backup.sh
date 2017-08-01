ansible-playbook --connection local -i "localhost," ci/ansible/pulp_backup.yaml \
    -e "pulp_build=${PULP_BUILD}" \
    -e "pulp_version=${PULP_VERSION}" \
    -e "rhn_password=${RHN_PASSWORD}" \
    -e "rhn_pool=${RHN_POOL}" \
    -e "rhn_username=${RHN_USERNAME}" \
    -e "local_bkup_dir=${PWD}/local_backups" \
    -e "remote_bkup_dir=${PWD}" \
    -e "fetch_to_localhost=false" \
    -e "test_results_dir=${PWD}"
