#!/usr/bin/env bash

# stop and remove pulp-related containers
for NAME in worker1 worker2 pulpapi crane beat resource_manager 
do
    echo stopping and removing $NAME
    docker stop $NAME > /dev/null
    docker rm $NAME > /dev/null
done
