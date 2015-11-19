#!/usr/bin/env bash

# the "docker root" as I'm calling it, which is where all shared and persistent
# storage is located for the pulp containers.
# trailing slash is removed if present
DROOT=$(echo $1 | sed -e 's/\/$//')

if [ -z $DROOT ]
then
    echo "specify a directory in which to store data" 1>&2
    exit 1
fi

if [ ! -d $DROOT ]
then
    echo "specified path is not a directory" 1>&2
    exit 1
fi


echo Launching in $DROOT

# check if a directory exists, and if not, make it
function ensure_dir {
    if [ ! -d $DROOT$1 ]
    then
        echo creating $DROOT$1
        mkdir -p $DROOT$1
    fi
}

# make sure all of these directories exist
ensure_dir /var/log/httpd-pulpapi
ensure_dir /var/log/httpd-crane
ensure_dir /etc/pulp
ensure_dir /etc/pki/pulp
ensure_dir /var/lib/pulp
ensure_dir /var/lib/pulp/celery

LINKS="--link qpid:qpid --link db:db"
MOUNTS="-v $DROOT/etc/pulp:/etc/pulp -v $DROOT/etc/pki/pulp:/etc/pki/pulp -v $DROOT/var/lib/pulp:/var/lib/pulp -v /dev/log:/dev/log"

# try to start an existing one, and only run a new one if that fails
if docker start db 2> /dev/null
then
    echo db already exists
else
    echo running db
    docker run -d --name db -p 27017:27017 pulp/mongodb
fi

# try to start an existing one, and only run a new one if that fails
if docker start qpid 2> /dev/null
then
    echo qpid already exists
else
    echo running qpid
    docker run -d --name qpid -p 5672:5672 pulp/qpid
fi

# run the setup script that populates $DROOT with boiler-plate config files and
# data directories
docker run -it --rm $LINKS $MOUNTS --hostname pulpapi pulp/base bash -c /setup.sh

docker run $MOUNTS $LINKS -d --name beat pulp/worker beat
docker run $MOUNTS $LINKS -d --name resource_manager pulp/worker resource_manager
docker run $MOUNTS $LINKS -d --name worker1 pulp/worker worker 1
docker run $MOUNTS $LINKS -d --name worker2 pulp/worker worker 2
docker run $MOUNTS -v $DROOT/var/log/httpd-pulpapi:/var/log/httpd $LINKS -d --name pulpapi --hostname pulpapi -p 443:443 -p 80:80 pulp/apache
docker run $MOUNTS -v $DROOT/var/log/httpd-crane:/var/log/httpd -d --name crane -p 5000:80 pulp/crane-allinone
