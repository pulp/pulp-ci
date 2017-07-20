#!/bin/bash

pulp-admin login -u "${PULP_USER:-admin}" -p "${PULP_PASSWORD:-admin}"

for repo in busybox docker registry; do
    pulp-admin docker repo list --repo-id "${repo}"
done
pulp-admin iso repo list --repo-id filerepo
pulp-admin puppet repo list --repo-id forge
pulp-admin python repo list --repo-id pypi
pulp-admin python repo list --repo-id python-upload
pulp-admin rpm repo list --repo-id centos5
pulp-admin rpm repo list --repo-id drpm
pulp-admin rpm repo list --repo-id file-feed
pulp-admin rpm repo list --repo-id rpm-signed
pulp-admin rpm repo list --repo-id srpm
pulp-admin rpm repo list --repo-id sync-schedule

if [[ -f "${CDN_CERTIFICATES}" ]]; then
    pulp-admin rpm repo list --repo-id rhel6
    pulp-admin rpm repo list --repo-id rhel7-rhn-tools
fi

pulp-admin logout
