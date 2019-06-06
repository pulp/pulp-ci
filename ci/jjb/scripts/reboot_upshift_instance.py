import os
import openstack.cloud
openstack.enable_logging(debug=True)

# connection

# By reading the clouds.yaml file
# conn = openstack.connect(cloud='openstack')

# By passing parameters
"""
export UPSHIFTINSTANCEPREFIX=foobar
export UPSHIFTUSER=my-username
export UPSHIFTPROJECTID=4389570597635298632fhbg8435u85
export UPSHIFTAUTHURL=https://xxx.xxx.xxxx.xxx.xxx.redhat.com:13000/v3
export UPSHIFTIMAGE=rhel-7.7-server-x86_64-latest
export UPSHIFTPASSWORD=sup3rs3c43t
export UPSHIFTPROJECTNAME=my-project
"""
# Config variables
AUTH_URL = os.environ.get('UPSHIFTAUTHURL')
USERNAME = os.environ.get('UPSHIFTUSER')
PASSWORD = os.environ.get('UPSHIFTPASSWORD')
PROJECT_ID = os.environ.get(
    'UPSHIFTPROJECTID',
    '144f871271034aa9960c449982fa36f7'
)
PROJECT_NAME = os.environ.get(
    'UPSHIFTPROJECTNAME',
    'pulp-jenkins'
)
DOMAIN_NAME = os.environ.get("UPSHIFTDOMAINNAME", "redhat.com")
INTERFACE = os.environ.get("UPSHIFTINTERFACE", "public")
IDENTITY_API_VERSION = os.environ.get("UPSHIFTIDENTITYAPIVERSION", '3')

# Connection
conn = openstack.connection.Connection(
    region_name='regionOne',
    auth=dict(
        auth_url=AUTH_URL,
        username=USERNAME,
        password=PASSWORD,
        project_id=PROJECT_ID,
        project_name=PROJECT_NAME,
        user_domain_name=DOMAIN_NAME,
    ),
    interface=INTERFACE,
    identity_api_version=IDENTITY_API_VERSION,
)

server = conn.get_server(os.environ.get('UPSHIFTSERVERID'))
conn.compute.reboot_server(server.id, "SOFT")
conn.compute.wait_for_server(server)
