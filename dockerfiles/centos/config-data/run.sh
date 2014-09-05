#!/bin/bash

# Modify /etc/pulp/server.conf with variables from 'docker run'
cp /etc/pulp/server.conf{,.orig}
sed -i "s/# seeds: localhost:27017/seeds: $MONGO_HOST:27017/" /etc/pulp/server.conf
sed -i "s/# server_name: server_hostname/server_name: $PULP_HOST/" /etc/pulp/server.conf
sed -i "s/# url: tcp:\/\/localhost:5672/url: tcp:\/\/$QPID_HOST:5672/" /etc/pulp/server.conf
sed -i "s/# broker_url: qpid:\/\/guest@localhost\//broker_url: qpid:\/\/guest@$QPID_HOST\//" /etc/pulp/server.conf
