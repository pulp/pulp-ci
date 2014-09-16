#!/usr/bin/env bash

for NAME in base apache admin-client mongodb qpid worker crane crane-allinone
do
    pushd $NAME
    docker build -t pulp/$NAME:latest .
    popd
done
