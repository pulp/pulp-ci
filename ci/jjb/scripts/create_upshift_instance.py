import os
import openstack.cloud
from uuid import uuid4
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
IMAGE = os.environ.get(
    'UPSHIFTIMAGE',
    'rhel-7.6-server-x86_64-released '
)
FLAVOR = os.environ.get("UPSHIFTFLAVOR", "ci.m3.medium")
NETWORK = os.environ.get("UPSHIFTNETWORK", "provider_net_shared_2")
INSTANCE_PREFIX = os.environ.get('UPSHIFTINSTANCEPREFIX', 'default')
KEYNAME = os.environ.get("UPSHIFTKEYNAME", "jenkins")

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

# entities
image = conn.image.find_image(IMAGE)
flavor = conn.get_flavor(FLAVOR)
network = conn.network.find_network(NETWORK)

# instance
name = "{0}-{1}".format(INSTANCE_PREFIX, uuid4().hex)

server = conn.create_server(
    str(name),
    image=image,
    flavor=flavor,
    network=network,
    key_name=KEYNAME,
    wait=True,
    auto_ip=True,
)
# vm-10-0-79-72.hosted.upshift.rdu2.redhat.com.
hostname = "vm-{0}.hosted.upshift.rdu2.redhat.com".format(
    server.accessIPv4.replace('.', '-')
)

parameters = """
PULP_HOSTNAME={hostname}
UPSHIFTSERVERID={server_id}
"""

with open('parameters.txt', 'w') as param_file:
    param_file.write(
        parameters.format(
            hostname=hostname,
            server_id=server.id
        )
    )

print("Instance ID:", server.id)
print("IP:", server.accessIPv4)
print("Hostname:", hostname)

if os.environ.get('UPSHIFTDEBUG'):
    import ipdb; ipdb.set_trace()
