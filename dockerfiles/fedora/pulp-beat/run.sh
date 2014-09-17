#!/bin/sh

set -x

#
# Use the test_db_available.py script to poll for the DB server
#
wait_for_database() {
    DB_TEST_TRIES=12
    DB_TEST_POLLRATE=5
    TRY=0
    while [ $TRY -lt $DB_TEST_TRIES ] && ! /test_db_available.py 
    do
	TRY=$(($TRY + 1))
	echo "Try #${TRY}: DB unavailable - sleeping ${DB_TEST_POLLRATE}"
	sleep $DB_TEST_POLLRATE
    done
    if [ $TRY -ge $DB_TEST_TRIES ]
    then
	echo "Unable to contact DB after $TRY tries: aborting container"
        exit 2
    fi
}

#
# Create the initial database for Pulp
#
initialize_database() {
    # why apache? MAL
    runuser apache -s /bin/bash /bin/bash -c "/usr/bin/pulp-manage-db"
}


#
# Begin running the Pulp Resource Manager worker
# 
run_resource_manager() {
       exec runuser apache \
      -s /bin/bash \
      -c "/usr/bin/celery worker -c 1 -n resource_manager@$PULP_SERVER_NAME \
          --events --app=pulp.server.async.app \
          --umask=18 \
          --loglevel=INFO -Q resource_manager \
          --logfile=/var/log/pulp/resource_manager.log"
}

# =============================================================================
# Main
# =============================================================================
#

#
# First, initialize the pulp server configuration
#
if [ ! -x /configure_pulp_server.sh ]
then
  echo >&2 "Missing required initialization script for pulp server: /configure_pulp_server.sh"
  exit 2
fi
. /configure_pulp_server.sh

if [ ! -x /test_db_available.py ] 
then
  echo >&2 "Missing required initialization script for pulp server: /test_db_available.py"
  exit 2
fi
wait_for_database

#
# The celery beat service is the scheduling heart of the pulp service
#
run_resource_manager
