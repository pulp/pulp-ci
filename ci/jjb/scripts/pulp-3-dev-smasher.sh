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
        "version": "3"
    },
    "systems": [
        {
            "hostname": "$(hostname --long)",
            "roles": {
                "amqp broker": {"service": "rabbitmq"},
                "api": {"scheme": "http"},
                "mongod": {},
                "pulp celerybeat": {},
                "pulp cli": {},
                "pulp resource manager": {},
                "pulp workers": {},
                "shell": {},
                "squid": {}
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
