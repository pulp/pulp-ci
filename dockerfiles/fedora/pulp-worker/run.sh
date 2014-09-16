#!/bin/bash

# Display startup activity
set -x

WORKER_NUMBER=$1
if [ -z "$WORKER_NUMBER" ]
then
    exit "Missing required argument: worker number"
fi

# Take settings from Kubernetes service environment unless they are explicitly
# provided
PULP_SERVER_CONF=${PULP_SERVER_CONF:=/etc/pulp/server.conf}

PULP_SERVER_NAME=${PULP_SERVER_NAME:=pulp.example.com}

DB_SERVICE_HOST=${DB_SERVICE_HOST:=${SERVICE_HOST}}
DB_SERVICE_PORT=${DB_SERVICE_PORT:=27017}

MSG_SERVICE_HOST=${MSG_SERVICE_HOST:=${SERVICE_HOST}}
MSG_SERVICE_PORT=${MSG_SERVICE_PORT:=5672}

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
    sed -i -e "s/%PULP_SERVER_NAME%/${PULP_SERVER_NAME}/" ${PULP_SERVER_CONF}
}

#
# Set the messaging server access information
#
configure_messaging() {
    sed -i \
        -e "s/%MSG_SERVICE_HOST%/${MSG_SERVICE_HOST}/" \
        -e "s/%MSG_SERVICE_PORT%/${MSG_SERVICE_PORT}/" \
        $PULP_SERVER_CONF
}

#
# Set the database access information
#
configure_database() {
    sed -i \
        -e "s/%DB_SERVICE_HOST%/${DB_SERVICE_HOST}/" \
        -e "s/%DB_SERVICE_PORT%/${DB_SERVICE_PORT}/" \
        $PULP_SERVER_CONF
}

#
# Begin running the Pulp Resource Manager worker
# 
start_worker() {
    # WORKER_NUMBER=$1
    # PULP_SERVER_NAME=$2
    exec runuser apache \
	-s /bin/bash \
	-c "/usr/bin/celery worker \
	--events --app=pulp.server.async.app \
	--loglevel=INFO \
	-c 1 \
        --umask=18 \
	-n reserved_resource_worker-$1@$2 \
	--logfile=/var/log/pulp/reserved_resource_worker-$1.log"

}
# =============================================================================
# Main
# =============================================================================
check_config_target

configure_server_name
configure_database
configure_messaging

start_worker $WORKER_NUMBER $PULP_SERVER_NAME
