#!/bin/bash

pulp-admin login -u "${PULP_USER}" -p "${PULP_PASSWORD}"

pulp-admin rpm repo list --repo-id drpm
pulp-admin rpm repo list --repo-id srpm
pulp-admin rpm repo list --repo-id rhel6
pulp-admin rpm repo list --repo-id centos5
pulp-admin rpm repo list --repo-id zoo
pulp-admin puppet repo list --repo-id forge
pulp-admin rpm repo list --repo-id repo_1
pulp-admin rpm repo list --repo-id file-feed
pulp-admin iso repo list --repo-id filerepo
if [ "$(echo -e 2.8\\n${PULP_VERSION} | sort -V | head -n 1)" = "2.8" ]; then
    pulp-admin docker repo list --repo-id busybox
fi
pulp-admin rpm repo list --repo-id rhel7-rhn-tools

pulp-admin logout
