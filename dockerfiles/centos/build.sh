#!/usr/bin/env bash

# Exit the loops if any build command fails
set -e

for NAME in base apache admin-client mongodb qpid worker crane crane-allinone
do
    pushd $NAME
    docker build -t pulp/$NAME:latest .
    popd
done
