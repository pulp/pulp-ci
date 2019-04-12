#!/bin/bash
sudo dnf -y update
sudo dnf -y install ansible git curl

host="localhost"
hostname="$(hostname --long)"

export PULP3_HOST=$host
export PULP3_ANSIBLE_CONNECTION=local
export PULP3_CONTENT_HOST=$hostname
export PULP3_QE_TOOLS_BRANCH=master
export PULP3_QE_TOOLS_USER=PulpQE

curl https://raw.githubusercontent.com/"${PULP3_QE_TOOLS_USER}"/pulp-qe-tools/"${PULP3_QE_TOOLS_BRANCH}"/pulp3/install_pulp3/install.sh | bash
