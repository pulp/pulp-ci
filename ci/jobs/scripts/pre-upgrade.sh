#!/bin/bash

if [[ -f "${CDN_CERTIFICATES}" ]]; then
    tar -zxvf "${CDN_CERTIFICATES}"
fi

pulp-admin login -u "${PULP_USER}" -p "${PULP_PASSWORD}"

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
    --feed https://cdn.redhat.com/content/dist/rhel/rhui/server/6/6.7/x86_64/kickstart/ \
    --feed-ca-cert cdn/cdn.redhat.com-chain.crt \
    --feed-cert cdn/914f702153514b06c1ef279db9dcadce.crt \
    --feed-key cdn/914f702153514b06c1ef279db9dcadce.key \
    --remove-missing true \
    --repo-id rhel6 \
    --serve-http true
pulp-admin rpm repo sync run --repo-id rhel6

pulp-admin rpm repo create \
    --checksum-type sha \
    --feed http://ftp.linux.ncsu.edu/pub/CentOS/5.11/os/x86_64/ \
    --repo-id centos5 \
    --serve-http true \
    --skip erratum
pulp-admin rpm repo sync run --repo-id centos5

pulp-admin rpm repo create \
    --feed http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/zoo \
    --relative-url zoo \
    --repo-id zoo \
    --retain-old-count 0

pulp-admin rpm repo sync run --repo-id zoo
pulp-admin rpm repo sync schedules create \
    --repo-id zoo \
    --schedule 2015-06-06T14:29:00Z/PT1M

pulp-admin puppet repo create \
    --feed http://forge.puppetlabs.com \
    --repo-id forge
pulp-admin puppet repo sync run --repo-id forge

pulp-admin rpm repo create \
    --feed http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/ \
    --repo-id repo_1

pulp-admin rpm repo create \
    --feed file:///var/lib/pulp/published/yum/https/repos/repos/pulp/pulp/demo_repos/zoo/ \
    --repo-id file-feed
pulp-admin rpm repo sync run --repo-id file-feed

pulp-admin iso repo create \
    --feed https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_file_repo/ \
    --repo-id filerepo
pulp-admin iso repo sync run --repo-id filerepo

if [ "$(echo -e 2.8\\n${PULP_VERSION} | sort -V | head -n 1)" = "2.8" ]; then
    pulp-admin docker repo create \
        --feed https://index.docker.io \
        --repo-id busybox \
        --upstream-name busybox
    pulp-admin docker repo sync run --repo-id busybox
fi

pulp-admin repo group create --group-id my-zoo --display-name "My Zoo"
pulp-admin repo group members add  --group-id my-zoo --repo-id zoo

pulp-admin rpm repo create \
    --feed https://cdn.redhat.com/content/dist/rhel/rhui/server/7/7Server/x86_64/rhn-tools/os/ \
    --feed-ca-cert cdn/cdn.redhat.com-chain.crt \
    --feed-cert cdn/914f702153514b06c1ef279db9dcadce.crt \
    --feed-key cdn/914f702153514b06c1ef279db9dcadce.key \
    --repo-id rhel7-rhn-tools \
    --skip erratum
pulp-admin rpm repo sync run --repo-id rhel7-rhn-tools

pulp-admin logout
