#!/usr/bin/env bash

mkdir -p ~/.virtualenvs/
python3 -m venv ~/.virtualenvs/pulp-smash/
bin_dir="$(realpath --canonicalize-existing ~/.virtualenvs/pulp-smash/bin/)"
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
# clone all repos to run tests
mkdir -p ~/p3-tests/
cd ~/p3-tests/ || exit
# pulp core
git clone https://github.com/pulp/pulp --branch master
# pulp file
git clone https://github.com/pulp/pulp_file --branch master
# pulp rpm
git clone https://github.com/pulp/pulp_rpm.git --branch master
# pulp docker
git clone https://github.com/pulp/pulp_docker.git --branch master
py.test -v --color=yes --junit-xml=junit-report.xml --pyargs pulp/pulpcore/tests/functional pulp_file/pulp_file/tests/functional pulp_rpm/pulp_rpm/tests/functionalI pulp_docker/pulp_docker/tests/functional
test -f junit-report.xml
