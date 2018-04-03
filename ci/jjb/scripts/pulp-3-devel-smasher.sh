os_release_name="$(source /etc/os-release && echo "${NAME}")"
if [ "${os_release_name}" == "Red Hat Enterprise Linux Server" ]; then
    prefix='scl enable rh-python36 --'
else
    prefix=''
fi

mkdir -p ~/.virtualenvs/
${prefix} python3 -m venv ~/.virtualenvs/pulp-smash/
bin_dir="$(realpath --canonicalize-existing ~/.virtualenvs/pulp-smash/bin/)"
${prefix} "${bin_dir}/pip" install --upgrade pip
${prefix} "${bin_dir}/pip" install git+https://github.com/PulpQE/pulp-smash.git#egg=pulp-smash
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
                "amqp broker": {"service": "qpidd"},
                "api": {"port": 8000, "scheme": "http"},
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
${prefix} "${bin_dir}/pulp-smash" settings path
${prefix} "${bin_dir}/pulp-smash" settings show
${prefix} "${bin_dir}/pulp-smash" settings validate
# Use pytest instead of unittest for XML reports. :-(
${prefix} "${bin_dir}/pip" install pytest
${prefix} "${bin_dir}/py.test" -v --color=yes --junit-xml=junit-report.xml --pyargs pulp_smash.tests
test -f junit-report.xml
