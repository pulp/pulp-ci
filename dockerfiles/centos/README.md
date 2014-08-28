# Centos Dockerfiles

Each directory contains a Dockerfile to build the docker image for that pulp service or component.

**NOTE: This deployment is not secure enough to be used in a production environment.** More testing and hardening work needs to be done.

Run `./install_pulp_server.sh` to pull and start all the containers for a multi-container pulp server. See the [Pulp Docker Registry quickstart guide](../docker-quickstart.rst) for deploying Pulp as a multi-container environment and using Pulp as a docker registry.

## Known issues:
* insecure QPID configuration
* insecure MongoDB configuration
* self-signed SSL certificates are created during deployment run-time
* no support for adding CA-signed certificates to deployment
* no configuration support. There are many options to achieve this, including mounting a custom local config file in the container(s), environment variable replacement or using a key:value store such as etcd.
* no container orchestration support. Complex, multi-container applications should be managed by a service such as kubernetes.
* persistent storage strategy not documented
