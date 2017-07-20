echo "Start upgrading Pulp on ${INSTANCE_IP}..."
alias ssh="ssh -tt -o StrictHostKeyChecking=no cloud-user@${INSTANCE_IP}"
ssh exit 0
ssh sudo katello-service stop
ssh rpm -qa | grep pulp
ssh rpm -q satellite
ssh sudo yum -y install yum-utils
ssh sudo yum-config-manager --add-repo "${PULP_UPGRADE_REPO_URL}"
ssh sudo yum repolist enabled | grep pulp
# We can't add EPEL repository, that avoids package conflict. We still need to
# install python-billiard from EPEL though
ssh sudo yum -y install http://dl.fedoraproject.org/pub/epel/7/x86_64/p/python-billiard-3.3.0.20-2.el7.x86_64.rpm

ssh sudo yum update -y --nogpgcheck
ssh rpm -qa | grep pulp
ssh rpm -qa | grep python

# We need mongod started to run pulp-manage-db. Don't call katello-service
# restart because pulp-manage-db won't do anything if some of pulp processes
# are running.
ssh sudo systemctl start mongod
ssh sudo -u apache pulp-manage-db
ssh sudo katello-service start

UPDATE_PULP_VERSION="$(ssh rpm -qa | grep pulp-server | awk -F'-' '{ print $3 }')"
echo "Pulp upgraded to ${UPDATE_PULP_VERSION} version."
