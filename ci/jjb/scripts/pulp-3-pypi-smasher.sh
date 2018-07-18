mkdir -p ~/.virtualenvs/pulp-smash/
python3 -m venv ~/.virtualenvs/pulp-smash
source ~/.virtualenvs/pulp-smash/bin/activate
pip install --upgrade pip
pip install git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash
mkdir -p ~/.config/pulp_smash
cat >~/.config/pulp_smash/settings.json <<EOF
{
    "pulp": {
        "auth": ["admin", "admin"],
        "selinux enabled": false,
        "version": "3"
    },
    "hosts": [
        {
            "hostname": "$(hostname --long)",
            "roles": {
                "api": {"port": 8000, "scheme": "http", "service": "nginx"},
                "pulp resource manager": {},
                "pulp workers": {},
                "redis": {},
                "shell": {}
            }
        }
    ]
}
EOF
pulp-smash settings path
pulp-smash settings show
pulp-smash settings validate
# Use pytest instead of unittest for XML reports. :-(
pip install pytest
py.test -v --color=yes --junit-xml=junit-report.xml --pyargs pulp_smash.tests
test -f junit-report.xml
