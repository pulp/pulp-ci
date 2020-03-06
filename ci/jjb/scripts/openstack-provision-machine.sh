source "${OPENSTACK_CREDENTIALS}"
source "${REMOTE_JENKINS_CREDENTIALS}"

sudo dnf -y install python-devel redhat-rpm-config wget
sudo pip install -U pip virtualenv
virtualenv satellite-pulp
source satellite-pulp/bin/activate
pip install python-openstackclient

# Only underscores, hyphens, and alphanumeric characters are allowed for
# keypair names
KEY_NAME="pulp-jenkins"
IMAGE_ID="$(openstack image show -f value -c id "rhel-7.3-server-x86_64-updated")"

# Upload SSH key pair for OpenStack instance.
if ! openstack keypair list | grep -q "${KEY_NAME}"; then
    echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC6DJ8fmd61DWPCMiOEuy96ajI7rL3rWu7C9NQhE9a4SfyaiBcghREHJNCz9LGJ57jtOmNV0+UEDhyvTckZI2YQeDqGCP/xO9B+5gQNlyGZ9gSmFz+68NhYQ0vRekikpb9jNdy6ZZbfZDLp1w7dxqDIKfoyu7QO3Qr3E/9CpiucQif2p+oQOVOCdKEjvGYNkYQks0jVTYNRscgmcezpfLKhqWzAre5+JaMB0kRD5Nqadm2uXKZ4cNYStrpZ4xUrnMvAqjormxW2VJNx+0716Wc2Byhg8Nva+bsOkxp/GewBWHfNPtzQGMsL7oYZPtOd/LrmyYeu/M5Uz7/6QCv4N90P pulp" > pulp-jenkins.pub
    echo "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAzoPajR2xtQOAfBebX69Mx9Ee4P/LMqlxQLKvF0bc79/1ayMf3IrmpY1V6JCpABvMV1830I9D9x9Tr8E9zjg2wWT14hhHsrUKSWUsy3doIwz3MtISBZPMig5AizVjH6Wl/t833zgkeHtStCYI/bmJQykj6AgB8/A4L5SRIpNnl1q7V+sw37Rmumaiqu4lRDXyTXY7mlOCuxrus/WcGyVTh2k+oBVqkz2V2s3+Or8Zy2Y441B4z3vF3lE6aoIBwidBVZ1LKaofZDMRf/lu575cI4AB3N5DQvpqwLSc4+HIvog0FdKUo3qMaFgg0KNkYS5fnpDpRDRQnFw7oFnBHiPNqw== jenkins@satellite-jenkins" >> pulp-jenkins.pub
    openstack keypair create --public-key pulp-jenkins.pub "${KEY_NAME}"
fi

# Setup security group rules.
if ! openstack security group list | grep -q "${KEY_NAME}"; then
    openstack security group create --description "Security group for Satellite6-Pulp testing" "${KEY_NAME}"
fi

if ! openstack security group rule list "${KEY_NAME}" | grep -q "0.0.0.0/0"; then
    openstack security group rule create --protocol icmp "${KEY_NAME}"
    for tcp_port in 22 80 443 5000 5646 5647 5671 8000 8140 8443 9090; do
        openstack security group rule create --protocol tcp --dst-port "${tcp_port}" "${KEY_NAME}"
    done
    for udp_port in 53 69; do
        openstack security group rule create --protocol udp --dst-port "${udp_port}" "${KEY_NAME}"
    done
fi

# Check if there is an instance running and delete it
if [ "$(nova list | grep ${INSTANCE_NAME})" ]; then
    nova delete "${INSTANCE_NAME}"
    while [ "$(nova list | grep ${INSTANCE_NAME})" ]; do
        sleep 5
    done
fi

ROUTER="$(openstack router list -f value -c "ID" -c "Name" | grep "default-satellite-jenkins" | cut -f1 -d' ')"
EXTERNAL_GATEWAY_INFO="$(openstack router show -f value -c external_gateway_info "${ROUTER}")"
#NETWORK="$(python3 <<EOF
#import json
#data = json.loads('${EXTERNAL_GATEWAY_INFO}')
#print(data['network_id'])
#EOF
#)"
#do not use the default shared network.
NETWORK='provider_net_shared_2'

FLOATING_IP="$(openstack floating ip list -f value -c "Floating IP Address" --network "${NETWORK}" --status DOWN | head -n 1)"

if [ ! "${FLOATING_IP}" ]; then
    openstack floating ip create "${NETWORK}"
    FLOATING_IP="$(openstack floating ip list -f value -c "Floating IP Address" --network "${NETWORK}" --status DOWN | head -n 1)"
fi

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
    --key-name "${KEY_NAME}" \
    --security-groups "${KEY_NAME}" \
    --user-data cloud-config.txt \
    "${INSTANCE_NAME}"
COUNTER=1
while ! nova list --status ACTIVE | grep Running | grep -q "${INSTANCE_NAME}"; do
    echo "The network is not yet ready ${COUNTER} times..."
    let COUNTER+=1
    if [[ ${COUNTER} -gt 60 ]]; then
        echo "The OpenStack instance was failed to create..."
        exit 1
    fi
    sleep 1
done
INSTANCE_ID="$(nova list | grep "${INSTANCE_NAME}" | awk '{ print $2 }' | head -1)"

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
