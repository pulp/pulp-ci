#!/usr/bin/env bash
set -euo pipefail

if [ "${UPGRADE_OS}" = "true" ]; then
# start upgrade part

ssh cloud-user@${PULP_HOSTNAME} << EOF
sudo bash -c 'cat > /etc/yum.repos.d/rhellatest.repo' <<- HERE
	[rhellatest]
	name=rhellatest
	baseurl="${OS_LATEST_REPO}"
	enabled=1
	gpgcheck=0
	
	[rhellatestoptional]
	name=rhellatestoptional
	baseurl="${OS_LATEST_REPO_OPTIONAL}"
	enabled=1
	gpgcheck=0
	HERE
EOF

ssh cloud-user@${PULP_HOSTNAME} << EOF
pulp-admin -v status
echo "Pre upgrade version:"
cat /etc/os-release
sudo yum repolist
sudo systemctl stop httpd pulp_workers pulp_resource_manager pulp_celerybeat pulp_streamer
sudo yum update -y
sudo yum upgrade -y
sudo -u apache pulp-manage-db
sudo systemctl start httpd pulp_workers pulp_resource_manager pulp_celerybeat pulp_streamer
sleep 2
pulp-admin -v status
echo "Post upgrade version:"
cat /etc/os-release
EOF

sudo pip install -U pip virtualenv
virtualenv pulp-jenkins
source pulp-jenkins/bin/activate
pip install openstacksdk==0.31.1

python ci/jjb/scripts/reboot_upshift_instance.py

echo "$PULP_HOSTNAME"

# wait for ssh connection
sleep 60

# end upgrade part
fi
