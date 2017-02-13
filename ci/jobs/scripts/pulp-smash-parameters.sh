echo "BASE_URL=https://$(hostname --long)" > parameters.txt
PULP_RPM_VERSION="$(rpm -qa pulp-server | cut -d- -f3)"
if [ "${PULP_VERSION}" != "$(cut -d. -f-2 <<< "${PULP_RPM_VERSION}")" ]; then
    echo "Pulp RPM version ${PULP_RPM_VERSION} is not in the ${PULP_VERSION} series"
    exit 1
fi
echo "PULP_VERSION=${PULP_RPM_VERSION}" >> parameters.txt
cp /etc/pki/CA/cacert.pem cacert.pem
