source "${OPENSTACK_CREDENTIALS}"
source "${REMOTE_JENKINS_CREDENTIALS}"

sudo dnf -y install python-devel redhat-rpm-config wget
sudo pip install -U pip virtualenv
virtualenv satellite-pulp
source satellite-pulp/bin/activate
pip install python-glanceclient python-novaclient

# Only underscores, hyphens, and alphanumeric characters are allowed for
# keypair names
KEY_NAME="pulp-jenkins"
IMAGE_ID="$(glance image-list | grep '| rhel-7.3-server-x86_64-updated' | awk '{ print $2 }')"

# Upload SSH key pair for OpenStack instance.
if [[ -z "$(nova keypair-list | grep ${KEY_NAME} | awk '{ print $2 }')" ]]; then
    echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC6DJ8fmd61DWPCMiOEuy96ajI7rL3rWu7C9NQhE9a4SfyaiBcghREHJNCz9LGJ57jtOmNV0+UEDhyvTckZI2YQeDqGCP/xO9B+5gQNlyGZ9gSmFz+68NhYQ0vRekikpb9jNdy6ZZbfZDLp1w7dxqDIKfoyu7QO3Qr3E/9CpiucQif2p+oQOVOCdKEjvGYNkYQks0jVTYNRscgmcezpfLKhqWzAre5+JaMB0kRD5Nqadm2uXKZ4cNYStrpZ4xUrnMvAqjormxW2VJNx+0716Wc2Byhg8Nva+bsOkxp/GewBWHfNPtzQGMsL7oYZPtOd/LrmyYeu/M5Uz7/6QCv4N90P pulp" > pulp-jenkins.pub
    echo "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAzoPajR2xtQOAfBebX69Mx9Ee4P/LMqlxQLKvF0bc79/1ayMf3IrmpY1V6JCpABvMV1830I9D9x9Tr8E9zjg2wWT14hhHsrUKSWUsy3doIwz3MtISBZPMig5AizVjH6Wl/t833zgkeHtStCYI/bmJQykj6AgB8/A4L5SRIpNnl1q7V+sw37Rmumaiqu4lRDXyTXY7mlOCuxrus/WcGyVTh2k+oBVqkz2V2s3+Or8Zy2Y441B4z3vF3lE6aoIBwidBVZ1LKaofZDMRf/lu575cI4AB3N5DQvpqwLSc4+HIvog0FdKUo3qMaFgg0KNkYS5fnpDpRDRQnFw7oFnBHiPNqw== jenkins@satellite-jenkins" >> pulp-jenkins.pub
    nova keypair-add --pub-key pulp-jenkins.pub "${KEY_NAME}"
fi

# Setup security group rules.
if [[ -z "$(nova secgroup-list | grep ${KEY_NAME})" ]]; then
    nova secgroup-create "${KEY_NAME}" "Security group for Satellite6-Pulp testing"
fi

if [[ -z $(nova secgroup-list-rules "${KEY_NAME}" | grep "0.0.0.0/0") ]]; then
    nova secgroup-add-rule "${KEY_NAME}" icmp -1 -1 0.0.0.0/0
    for tcp_port in 22 80 443 5000 5646 5647 5671 8000 8140 8443 9090; do
        nova secgroup-add-rule "${KEY_NAME}" tcp $tcp_port $tcp_port 0.0.0.0/0
    done
    for udp_port in 53 69; do
        nova secgroup-add-rule "${KEY_NAME}" udp $udp_port $udp_port 0.0.0.0/0
    done
fi

# Check if there is an instance running and delete it
if [ "$(nova list | grep ${INSTANCE_NAME})" ]; then
    nova delete "${INSTANCE_NAME}"
    while [ "$(nova list | grep ${INSTANCE_NAME})" ]; do
        sleep 5
    done
fi

FLOATING_IP="$(nova floating-ip-list | grep '| -' | awk '{ print $4 }' | head -n 1)"
INSTANCE_HOSTNAME="host-$(echo ${FLOATING_IP} | cut -d. -f 2- | sed 's/\./-/g')"
INSTANCE_FQDN="${INSTANCE_HOSTNAME}.host.centralci.eng.rdu2.redhat.com"
cat > cloud-config.txt << EOF
#cloud-config
fqdn: ${INSTANCE_FQDN}
hostname: ${INSTANCE_HOSTNAME}
manage_etc_hosts: true
EOF

nova boot --flavor 'm4.xlarge' \
    --image "${IMAGE_ID}" \
    --key-name $KEY_NAME \
    --security-groups "${KEY_NAME}" \
    --user-data cloud-config.txt \
    "${INSTANCE_NAME}"
COUNTER=1
while [[ -z "$(nova list | grep -e ACTIVE -e Running | grep ${INSTANCE_NAME})" ]]; do
    echo "The network is not yet ready ${COUNTER} times..."
    let COUNTER+=1
    if [[ ${COUNTER} -gt 60 ]]; then
        echo "The OpenStack instance was failed to create..."
        exit 1
    fi
    sleep 1
done
INSTANCE_ID="$(nova list | grep ${INSTANCE_NAME} | awk {' print $2 '} | head -1)"

# Associate the floating IP
nova floating-ip-associate "${INSTANCE_ID}" "${FLOATING_IP}"

# Wait until the OpenStack instance can be connected by SSH sessions.
# The following trigger builders will depend on SSH connectivity.
set +e
COUNTER=0
while true; do
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "cloud-user@${FLOATING_IP}" echo ping
    if [[ $? = 0 ]]; then
        break
    fi
    let COUNTER+=1
    echo "${FLOATING_IP} is not yet ready for ${COUNTER} times...";
    sleep 5
done
set -e

# Create a properties file to inject variables into the environment.
{
    echo "KEY_NAME=${KEY_NAME}"
    echo "INSTANCE_IP=${FLOATING_IP}"
    echo "INSTANCE_HOSTNAME=${INSTANCE_HOSTNAME}"
    echo "INSTANCE_FQDN=${INSTANCE_FQDN}"
    echo "INSTANCE_ID=${INSTANCE_ID}"
    echo "SECURITY_GROUP_NAME=${SECURITY_GROUP_NAME}"
    echo "REMOTE_JENKINS_USERNAME=${REMOTE_JENKINS_USERNAME}"
    echo "REMOTE_JENKINS_API_TOKEN=${REMOTE_JENKINS_API_TOKEN}"
    echo "REMOTE_JENKINS_URL=${REMOTE_JENKINS_URL}"
} > jenkins_openstack.properties
