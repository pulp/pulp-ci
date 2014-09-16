#!/bin/sh

set -x

# Take settings from Kubernetes service environment unless they are explicitly
# provided
PULP_SERVER_CONF=${PULP_SERVER_CONF:=/etc/pulp/server.conf}
export PULP_SERVER_CONF

PULP_SERVER_NAME=${PULP_SERVER_NAME:=pulp.example.com}
export PULP_SERVER_NAME

SERVICE_HOST=${SERVICE_HOST:=127.0.0.1}
export SERVICE_HOST

DB_SERVICE_HOST=${DB_SERVICE_HOST:=${SERVICE_HOST}}
DB_SERVICE_PORT=${DB_SERVICE_PORT:=27017}
export DB_SERVICE_HOST DB_SERVICE_PORT

MSG_SERVICE_HOST=${MSG_SERVICE_HOST:=${SERVICE_HOST}}
MSG_SERVICE_PORT=${MSG_SERVICE_PORT:=5672}
MSG_SERVICE_USER=${MSG_SERVICE_USER:=guest}
export MSG_SERVICE_HOST MSG_SERVICE_PORT MSG_SERVICE_NAME

check_config_target() {
    if [ ! -f ${PULP_SERVER_CONF} ]
    then
        echo "Cannot find required config file ${PULP_SERVER_CONF}"
        exit 2  
    fi
}

#
# Set the Pulp service public hostname
#
configure_server_name() {
    augtool -s set \
       "/files/etc/pulp/server.conf/target[. = 'server']/server_name" \
       "${PULP_SERVER_NAME}"
}

#
# Set the messaging server access information
#
configure_messaging() {
    augtool -s set "/files/etc/pulp/server.conf/target[. = 'messaging']/url" \
	"tcp://${MSG_SERVICE_HOST}:${MSG_SERVICE_PORT}"
    augtool -s set \
	"/files/etc/pulp/server.conf/target[. = 'tasks']/broker_url" \
	"qpid://${MSG_SERVICE_USER}@${MSG_SERVICE_HOST}:${MSG_SERVICE_PORT}"
}

#
# Set the database access information
#
configure_database() {
    augtool -s set \
	"/files/etc/pulp/server.conf/target[. = 'database']/seeds" \
	"${DB_SERVICE_HOST}:${DB_SERVICE_PORT}"
}

# =============================================================================
# Main
# =============================================================================
check_config_target

configure_server_name
configure_database
configure_messaging
