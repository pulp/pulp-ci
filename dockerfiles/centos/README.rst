Centos Dockerfiles
==================

This is a collection of Dockerfiles and related files that enable a demo
installation of Pulp to be quickly deployed with Docker. With one command,
you can have a fully-functional Pulp deployment ready to use.

This deployment method is for demo purposes only. It may also serve as the basis
for developing a more robust deployment approach.

Each directory contains a Dockerfile to build the docker image for that Pulp
service or component.

.. note:: This deployment is not secure enough to be used in a production environment.** More testing and hardening work needs to be done.

Deployment
----------

.. note:: On some systems SELinux may cause permission failures. Until a proper configuration has been tested SELinux may need to be set to permissive mode as a workaround. Run command ``setenforce 0`` then run the ``start.sh`` script.

Run ``./start.sh /path/to/lotsof/storage`` to pull and start all of the
images for a multi-container Pulp server.

Pulp will populate the given path with files it needs, such as config files and
data directories. After running the start script for the first time, you can
modify any settings you like within that path and restart the Pulp containers.

Stopping
--------

Run ``./stop.sh`` to stop and remove all of the Pulp containers, not including
QPID and MongoDB. None of the Pulp containers contain state that is valuable,
so it is safe to throw them away. That is the containerization best practice!

You can then run the ``start.sh`` script again with the same file path, and it will
re-use the existing QPID and MongoDB containers.

Usage
-----

A shell can be run with the ``pulp/admin-client`` image and linked to the Pulp
API container. Run the following two commands to start the shell container and
login to Pulp.

::

    $ sudo docker run --rm -it --link pulpapi:pulpapi pulp/admin-client bash
    bash-4.2# pulp-admin login -u admin
    Enter password: 
    Successfully logged in. Session certificate will expire at Oct 28 02:01:03 2014
    GMT.


Pulp-Docker Registry Deployment
-------------------------------

See the [Pulp Docker Registry quickstart guide](../docker-quickstart.rst) for deploying Pulp as a multi-container environment and using Pulp as a docker registry.

Known issues
------------

* insecure QPID configuration
* insecure MongoDB configuration
* self-signed SSL certificates are created during deployment run-time
* no support for adding CA-signed certificates to deployment
* no container orchestration support. Complex, multi-container applications should be managed by a service such as kubernetes.
