#!/usr/bin/env bash

IMAGES=( "pulp/crane-allinone" \
         "pulp/worker" \
         "pulp/qpid" \
         "pulp/mongodb" \
         "pulp/apache" \
         "pulp/data" \
         "pulp/centosbase" )

CONTAINERS=( "pulp-crane" \
             "pulp-worker1" \
             "pulp-worker2" \
             "pulp-beat" \
             "pulp-resource_manager" \
             "pulp-qpid" \
             "pulp-mongodb" \
             "pulp-apache" \
             "pulp-data" )

usage() {
  echo "USAGE: `basename $0` <pulp_ip_address>|uninstall"
  exit 1
}

function private_ip() {
  local priv_ip=$(docker inspect --format '{{ .NetworkSettings.IPAddress }}' $(docker ps -l -q))
  echo $priv_ip
}

install() {

  PULP_HOST=$(hostname)

  echo "Using hostname '${PULP_HOST}'"
  echo "Pulling docker images. This may take several minutes."

  for i in "${IMAGES[@]}"; do sudo docker pull $i; done

  echo "Running docker images"

  sudo mkdir -p /run/pulp/mongo

  # mongo
  sudo docker run -d \
         -v /run/pulp/mongo:/var/lib/mongo \
         -p 27017:27017 \
         --name pulp-mongodb \
         pulp/mongodb

  MONGO_IP=$(private_ip)
  echo "Mongo private IP: ${MONGO_IP}"

  # qpid
  sudo docker run -d \
         -p 5672:5672 \
         --name pulp-qpid \
         pulp/qpid

  QPID_IP=$(private_ip)
  echo "qpid private IP: ${QPID_IP}"

  # data
  sudo docker run \
         -e PULP_HOST=${PULP_HOST} \
         -e MONGO_HOST=$MONGO_IP \
         -e QPID_HOST=$QPID_IP \
         --name pulp-data \
         pulp/data

  # apache -- creates/migrates pulp_database
  sudo docker run -d --privileged \
         -v /dev/log:/dev/log \
         --volumes-from pulp-data \
         -p 443:443 -p 8080:80 \
         -e APACHE_HOSTNAME=${PULP_HOST} \
         --name pulp-apache \
         pulp/apache

  # pulp workers
  sudo docker run -d --privileged \
         -e WORKER_HOST=${PULP_HOST} \
         -v /dev/log:/dev/log \
         --volumes-from pulp-data \
         --name pulp-worker1 \
         pulp/worker worker 1
  sudo docker run -d --privileged \
         -e WORKER_HOST=${PULP_HOST} \
         -v /dev/log:/dev/log \
         --volumes-from pulp-data \
         --name pulp-worker2 \
         pulp/worker worker 2
  sudo docker run -d --privileged \
         -v /dev/log:/dev/log \
         --volumes-from pulp-data \
         --name pulp-beat \
         pulp/worker beat
  sudo docker run -d --privileged \
         -e WORKER_HOST=${PULP_HOST} \
         -v /dev/log:/dev/log \
         --volumes-from pulp-data \
         --name pulp-resource_manager \
         pulp/worker resource_manager

  # crane
  sudo docker run -d \
         -p 80:80 \
         --volumes-from pulp-data \
         --name pulp-crane \
         pulp/crane-allinone

}

usage() {
  echo "USAGE: `basename $0` [uninstall]"
  exit 1
}

uninstall() {

  echo "Uninstalling Pulp server"
  for c in "${CONTAINERS[@]}"; do
    PID=$(docker ps | awk "/$c/ {print \$1}")
    echo "Stopping container ${c}"
    docker stop $PID
  done
  for c in "${CONTAINERS[@]}"; do
    PID=$(docker ps -a | awk "/$c/ {print \$1}")
    echo "Removing container ${c}"
    docker rm $PID
  done

}

case $1 in
  uninstall)
    uninstall
  ;;
  *) install
  ;;
esac

