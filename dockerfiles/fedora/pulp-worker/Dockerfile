#
# Pulp Worker service - coordinate activities
#
# Environment Variables:
#  DB_SERVER_HOST: name or IP address of the MongoDB server
#  DB_SERVER_PORT: TCP port for MongoDB (default: 27017)
#  MSG_SERVER_HOST: name or IP address of the qpid server
#  MSG_SERVER_PORT: TCP port for qpidd (default: 5672)
#  PULP_SERVER_NAME: The public server name of the HTTP services
#
# must be started with -v /dev/log:/dev/log
#
FROM docker-registry.usersys.redhat.com/markllama/pulp-base

VOLUME [ "/var/www", "/var/lib/pulp" ]

ADD run.sh /run.sh

# Usage: /run.sh <worker number>
ENTRYPOINT ["/run.sh"]
