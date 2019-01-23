#!/bin/bash

# This script is used only by pulp-3-devel single node
# for the pulp3-*-dev-* jobs see script in pulp3-smash-runner.yaml 

echo "Is pulp working?"
curl -u admin:admin "$(hostname --long)":80/pulp/api/v3/status/ | python3 -m json.tool

mkdir -p ~/.virtualenvs/
python3 -m venv ~/.virtualenvs/pulp-smash/
source ~/.virtualenvs/pulp-smash/bin/activate
pip install --upgrade pip
pip install git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash
mkdir -p ~/.config/pulp_smash
cat >~/.config/pulp_smash/settings.json <<EOF
{
  "hosts": [
    {
      "hostname": "$(hostname --long)",
      "roles": {
        "api": {
          "port": 80,
          "scheme": "http",
          "service": "nginx",
          "verify": false
        },
        "pulp resource manager": {},
        "pulp workers": {},
        "redis": {},
        "shell": {
          "transport": "local"
        }
      }
    }
  ],
  "pulp": {
    "auth": [
      "admin",
      "admin"
    ],
    "selinux enabled": false,
    "version": "3.0"
  }
}
EOF
pulp-smash settings path
pulp-smash settings show
pulp-smash settings validate

pip install pytest
pip install pytest-sugar
pip install pytest-html

# clone all repos to run tests
# pulp core
git clone https://github.com/pulp/pulp --branch master
# pulp file
git clone https://github.com/pulp/pulp_file --branch master
# pulp rpm
git clone https://github.com/pulp/pulp_rpm.git --branch master
# pulp docker
git clone https://github.com/pulp/pulp_docker.git --branch master

# Run pytest
set +e
py.test -v --color=yes --html=report.html --self-contained-html --junit-xml=junit-report.xml pulp/pulpcore/tests/functional pulp_file/pulp_file/tests/functional pulp_rpm/pulp_rpm/tests/functional pulp_docker/pulp_docker/tests/functional
set -e

# check the report file exists
test -f junit-report.xml
