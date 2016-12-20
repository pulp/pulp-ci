#!/bin/bash

pulp-admin login -u "${PULP_USER:-admin}" -p "${PULP_PASSWORD:-admin}"

if [[ -f "${CDN_CERTIFICATES}" ]]; then
    tar -zxvf "${CDN_CERTIFICATES}"

    pulp-admin rpm repo create \
        --feed https://cdn.redhat.com/content/dist/rhel/rhui/server/6/6.7/x86_64/kickstart/ \
        --feed-ca-cert cdn/cdn.redhat.com-chain.crt \
        --feed-cert cdn/914f702153514b06c1ef279db9dcadce.crt \
        --feed-key cdn/914f702153514b06c1ef279db9dcadce.key \
        --remove-missing true \
        --repo-id rhel6 \
        --serve-http true
    pulp-admin rpm repo sync run --repo-id rhel6

    pulp-admin rpm repo create \
        --feed https://cdn.redhat.com/content/dist/rhel/rhui/server/7/7Server/x86_64/rhn-tools/os/ \
        --feed-ca-cert cdn/cdn.redhat.com-chain.crt \
        --feed-cert cdn/914f702153514b06c1ef279db9dcadce.crt \
        --feed-key cdn/914f702153514b06c1ef279db9dcadce.key \
        --repo-id rhel7-rhn-tools \
        --skip erratum
    pulp-admin rpm repo sync run --repo-id rhel7-rhn-tools
fi

pulp-admin rpm repo create \
    --feed https://repos.fedorapeople.org/pulp/pulp/fixtures/drpm-unsigned/ \
    --relative-url drpm \
    --repo-id drpm
pulp-admin rpm repo sync run --repo-id drpm

pulp-admin rpm repo create \
    --feed https://repos.fedorapeople.org/pulp/pulp/fixtures/srpm/ \
    --relative-url srpm \
    --repo-id srpm
pulp-admin rpm repo sync run --repo-id srpm

pulp-admin rpm repo create \
    --checksum-type sha \
    --feed http://mirror.centos.org/centos-5/5/os/x86_64/ \
    --repo-id centos5 \
    --serve-http true \
    --skip erratum
pulp-admin rpm repo sync run --repo-id centos5

pulp-admin rpm repo create \
    --feed https://repos.fedorapeople.org/pulp/pulp/fixtures/rpm-signed/ \
    --relative-url sync-schedule \
    --repo-id sync-schedule \
    --retain-old-count 0
pulp-admin rpm repo sync run --repo-id sync-schedule
pulp-admin rpm repo sync schedules create \
    --repo-id sync-schedule \
    --schedule 2015-06-06T14:29:00Z/PT1M

pulp-admin rpm repo create \
    --feed https://repos.fedorapeople.org/pulp/pulp/fixtures/rpm-signed/ \
    --relative-url rpm-signed \
    --repo-id rpm-signed \
    --serve-http true \
    --serve-https true
pulp-admin rpm repo sync run --repo-id rpm-signed
pulp-admin rpm repo publish run --repo-id rpm-signed

# The file-feed repo depends on the rpm-signed being published over https
pulp-admin rpm repo create \
    --feed file:///var/lib/pulp/published/yum/https/repos/rpm-signed/ \
    --repo-id file-feed
pulp-admin rpm repo sync run --repo-id file-feed


pulp-admin puppet repo create \
    --feed http://forge.puppetlabs.com \
    --queries puppetlabs \
    --repo-id forge
pulp-admin puppet repo sync run --repo-id forge

pulp-admin iso repo create \
    --feed https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_file_repo/ \
    --repo-id filerepo
pulp-admin iso repo sync run --repo-id filerepo

for repo in busybox docker registry; do
    pulp-admin docker repo create \
        --feed https://registry-1.docker.io \
        --repo-id "${repo}" \
        --upstream-name "${repo}"
    pulp-admin docker repo sync run --repo-id "${repo}"
done

pulp-admin python repo create \
    --feed https://pypi.python.org/ \
    --package-names requests,pulp-smash \
    --repo-id pypi
pulp-admin python repo sync run --repo-id pypi

pulp-admin python repo create --repo-id python-upload
git clone https://github.com/pulp/pulp_python.git --branch 0.0-dev
cd pulp_python/plugins || exit 1
./setup.py sdist
pulp-admin python repo upload --repo-id python-upload -f dist/pulp_python_plugins-0.0.0.tar.gz
pulp-admin python repo publish run --repo-id python-upload
cd - || exit 1

pulp-admin repo group create --group-id repo-group --display-name "Repo Group"
pulp-admin repo group members add  --group-id repo-group --repo-id sync-schedule

pulp-admin logout
