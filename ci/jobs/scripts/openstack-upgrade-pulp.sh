echo "Start upgrading Pulp on ${INSTANCE_IP}..."
alias ssh="ssh -tt -o StrictHostKeyChecking=no cloud-user@${INSTANCE_IP}"
ssh exit 0
ssh sudo katello-service stop
ssh rpm -qa | grep pulp
ssh rpm -q satellite
ssh sudo yum-config-manager --add-repo "${PULP_UPGRADE_REPO_URL}"
ssh sudo yum repolist enabled | grep pulp
ssh sudo yum update -y --nogpgcheck "pulp-*"
ssh rpm -qa | grep pulp
ssh sudo katello-service restart
ssh sudo -u apache pulp-manage-db
UPDATE_PULP_VERSION="$(ssh rpm -qa | grep pulp-server | awk -F'-' '{ print $3 }')"
echo "Pulp upgraded to ${UPDATE_PULP_VERSION} version."
