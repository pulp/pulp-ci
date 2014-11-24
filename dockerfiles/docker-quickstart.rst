Pulp Docker Registry Quickstart Guide
=====================================

This document explains how to use Pulp as a Docker registry. Its intended audience is Independent Software Vendors and Enterprise users who want to use Pulp as a Docker registry.

Pulp is a platform for managing repositories of content. Pulp makes it possible to locally mirror either all of or part of a repository. Pulp makes it possible to host content in new repositories, and makes it possible to manage content from multiple sources in a single place.

Pulp 2.5 with the pulp_docker plugin supports docker content and can serve as a docker registry.

Why Pulp As a Docker Registry?
------------------------------
Pulp provides the following:

* Separation of administrator interface (pulp API) and end-user interface (docker)
* Role-based access control (RBAC) with LDAP support
* Synchronization of content accross an organization using `nodes <https://pulp-user-guide.readthedocs.org/en/latest/nodes.html>`_.
* Promotion of content through user-defined environments, like "dev", "test", and "prod"
* `Well-documented API <https://pulp-dev-guide.readthedocs.org/en/latest/integration/rest-api/index.html>`_
* `Event-based notifications <https://pulp-dev-guide.readthedocs.org/en/latest/integration/events/index.html>`_ (http/amqp/email), that enable CI workflows and viewing history
* Read-only implementation of the docker registry API that can be deployed independently, making it very secure
* Service-oriented architecture (SOA) that enables scaling


Components
----------

+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pulp server                      | version 2.5 or greater. Includes a web server, mongo database and messaging broker                                                                              |
+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Pulp admin client                | remote management client, available as a `docker container <https://hub.docker.com/u/pulp/pulp-admin/>`_                                           |
+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pulp_docker plugin               | adds support for docker content type (`unreleased <https://github.com/pulp/pulp_docker>`_)                                                                      |
+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Crane                            | partial implementation of the `docker registry protocol <https://docs.docker.com/reference/api/registry_api/>`_ (`unreleased <https://github.com/pulp/crane>`_) |
+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+
| registry-admin.py                | prototype script based on pulp-admin client providing docker-focused managament of pulp registry                                                                |
+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+

Pulp packaged as a set of Docker images is based on the CentOS 7 image.

Click here to access the repository containing Dockerfiles for Pulp: `Dockerfile Source <https://github.com/pulp/pulp_packaging/blob/master/dockerfiles/centos>`_

Pulp Service Architecture
-------------------------

The Pulp Service Architecture is a multi-service application composed of an Apache web server, MongoDB and QPID for messaging. Tasks are performed using a Celery distributed task queue. Workers can be added to scale the architecture. Administrative commands are performed remotely using the pulp-admin client.

.. image:: pulp_component_architecture.png
The above figure details the deployment of the Pulp Service architecture.

+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Component** | **Role**                                                                                                                                                                          |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Apache        | Web server application (Pulp API) and serves files (RPMs, Docker images, etc). It responds to pulp-admin requests.                                                                |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| MongoDB       | Database                                                                                                                                                                          |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Crane         | An Apache server that responds to Docker Registry API calls. Implementation of the `Docker registry protocol <https://docs.docker.com/reference/api/registry_api/>`_.                                                                       |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| QPID          | The open-source messaging system that implements Apache Message Queuing Protocol (AMQP). Passes messages from Apache to CeleryBeat and the Pulp Resource Manager.                 |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Celery Beat   | Controls the task queue. See `explanation of Celery <https://fedorahosted.org/pulp/wiki/celery>`_                                                                                 |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Celery worker | Performs tasks in the queue. Multiple workers are spawned to handle load.                                                                                                         |
+---------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Deployment Options
------------------
Pulp can be deployed as a Docker registry in two different ways:

1. Pulp as a VM, with Crane as a Docker container. See `installation guide <https://pulp-user-guide.readthedocs.org/en/latest/installation.html>`_
2. A multi-container environment

This document focuses on the setup and configuration of the multi-container environment.

Server
------

.. warning:: This deployment is not intended to be used in a production environment. Additional testing and hardening work needs to be done.

Requirements
^^^^^^^^^^^^

* Host disk space

  * 1GB for server application
  * sufficient storage for MongoDB at ``/run/pulp/mongo``. `Install documentation <https://pulp-user-guide.readthedocs.org/en/pulp-2.4/installation.html#storage-requirements>`_ recommends 10GB or more.
  * sufficient storage for docker images at ``/var/lib/docker``

* DNS: The pulp server must have a resolvable hostname for the pulp-admin remote client to interact with it.
* docker v1.0 or higher

.. note:: The container-ized version of the Pulp server creates self-signed SSL certificates during run-time. The absence of a configuration option to use your organization's certificate is a known issue.

Configuration
^^^^^^^^^^^^^

1) Ensure the docker daemon is running and configured to run on startup

2) Open the following TCP ports to incoming traffic.

* 80 (HTTP)
* 443 (HTTPS)
* 5672 (QPID)
* 27017 (MongoDB)

Example commands using iptables::

        $ iptables -I INPUT -p tcp --dport 27017 -j ACCEPT
        $ iptables -I INPUT -p tcp --dport 80 -j ACCEPT
        $ iptables -I INPUT -p tcp --dport 443 -j ACCEPT
        $ iptables -I INPUT -p tcp --dport 5672 -j ACCEPT

Installation
^^^^^^^^^^^^

The Pulp server is packaged as a multi-container environment. It is a basic "all-in-one" deployment that requires the containers to run on the same VM or bare metal host.

#. Download the start script::

        $ curl -O https://raw.githubusercontent.com/pulp/pulp_packaging/master/dockerfiles/centos/start.sh

#. Run the start script. As the only argument, provide a full path to a
   directory where pulp can store its files. This will include config files and
   all of pulp's data.

        $ sudo ./start.sh /path/to/lots/of/storage/

#. Make any configuration changes within the path specified in the previous step,
   then stop and re-start the containers. See below for directions on stopping
   the containers.

#. View the images::

    $ sudo docker images| grep pulp
    pulp/crane-allinone       latest              4044c4e2fe2c        24 hours ago        309.7 MB
    pulp/crane                latest              e449467fa7c4        24 hours ago        309.7 MB
    pulp/worker               latest              d71d7f259d7f        24 hours ago        389.2 MB
    pulp/qpid                 latest              2902c9f82b14        24 hours ago        384.9 MB
    pulp/mongodb              latest              59e52ff43e67        24 hours ago        276.3 MB
    pulp/admin-client         latest              f3ae924b300c        24 hours ago        256.8 MB
    pulp/apache               latest              91480aecb981        24 hours ago        389.2 MB
    pulp/base                 latest              4f6a02d14c0d        24 hours ago        389.2 MB
    pulp/autotest             latest              718cf6ba577c        24 hours ago        671.7 MB

#. View all running containers::

    $ sudo docker ps
    CONTAINER ID        IMAGE                        COMMAND                CREATED             STATUS              PORTS                                      NAMES
    57ac643d8991        pulp/crane-allinone:latest   "/usr/sbin/httpd -D    6 minutes ago       Up 6 minutes        0.0.0.0:5000->80/tcp                       crane                                                                         
    6eef7dbaddaa        pulp/apache:latest           "/run.sh"              6 minutes ago       Up 6 minutes        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp   pulpapi                                                                       
    4a44dd49b1ec        pulp/worker:latest           "/run.sh worker 2"     6 minutes ago       Up 6 minutes                                                   worker2                                                                       
    3ccd9a72dbfb        pulp/worker:latest           "/run.sh worker 1"     6 minutes ago       Up 6 minutes                                                   worker1                                                                       
    7c6e5fb0e89e        pulp/worker:latest           "/run.sh resource_ma   6 minutes ago       Up 6 minutes                                                   resource_manager                                                              
    984546f26868        pulp/worker:latest           "/run.sh beat"         6 minutes ago       Up 6 minutes                                                   beat                                                                          
    9b60e58824d2        pulp/qpid:latest             "qpidd -t --auth=no"   6 minutes ago       Up 6 minutes        0.0.0.0:5672->5672/tcp                     beat/qpid,pulpapi/qpid,qpid,resource_manager/qpid,worker1/qpid,worker2/qpid   
    f2bc5e4b59d7        pulp/mongodb:latest          "/usr/bin/mongod --q   7 minutes ago       Up 6 minutes        0.0.0.0:27017->27017/tcp                   beat/db,db,pulpapi/db,resource_manager/db,worker1/db,worker2/db


Remote Client
-------------

The ``registry-admin.py`` is a prototype script providing docker-focused management of the Pulp registry. It is based on the ``pulp-admin`` client. To simplify installation, ``registry-admin.py`` runs the pulp-admin client as a container.

.. note:: Because the pulp-admin is run as a container you may be prompted for sudo password.

Requirements
^^^^^^^^^^^^

* access to Pulp server version 2.5 or greater with pulp_docker plugin enabled to support docker content type
* pulp registry credentials
* running docker service
* Python 2.7 or greater

Setup
^^^^^

1) Download the script::

        $ curl -O https://raw.githubusercontent.com/pulp/pulp_packaging/master/dockerfiles/registry-admin.py

2) Make it executable::

        $ chmod +x registry-admin.py

3) Login::

        $ ./registry-admin login
        Registry config file not found. Setting up environment.
        Creating config file /home/aweiteka/.pulp/admin.conf
        Enter registry server hostname: registry.example.com
        Verify SSL (requires CA-signed certificate) [False]: 
        User certificate not found.
        Enter registry username [aweiteka]: admin
        Enter registry password: 

        Pulling docker images
        Pulling repository pulp/pulp-admin
        8a01d78f4c70: Download complete


The default username is "admin" and the default password is "admin". Contact the Pulp system administrator for your username and password. A certificate is generated and used on subsequent commands. Credentials therefore do not need to be passed in for each command.

.. note:: The first time the script runs it will download the pulp/pulp-admin docker image from the Docker Hub.

4) If you are the administrator, change the default admin password::

        $ ./registry-admin.py pulp "auth user update --login admin --password newpass"
        User [admin] successfully updated

.. note:: A new container is created each time the pulp-admin runs. The ``--rm`` flag removes the ephemeral container after exiting. This adds a few seconds to execution and is optional.


Using the registry
^^^^^^^^^^^^^^^^^^

Push a docker image to the registry::

        $ ./registry-admin.py push my/app
        Repository [my-app] successfully created

        +----------------------------------------------------------------------+
                                      Unit Upload
        +----------------------------------------------------------------------+

        Extracting necessary metadata for each request...
        [==================================================] 100%
        Analyzing: test.tar
        ... completed

        Creating upload requests on the server...
        [==================================================] 100%
        Initializing: test.tar
        ... completed

        Starting upload of selected units. If this process is stopped through ctrl+c,
        the uploads will be paused and may be resumed later using the resume command or
        cancelled entirely using the cancel command.

        Uploading: test.tar
        [==================================================] 100%
        18944/18944 bytes
        ... completed

        Importing into the repository...
        This command may be exited via ctrl+c without affecting the request.


        [\]
        Running...

        Task Succeeded


        Deleting the upload request...
        ... completed

        +----------------------------------------------------------------------+
                              Publishing Repository [true]
        +----------------------------------------------------------------------+

        This command may be exited via ctrl+c without affecting the request.


        Publishing Image Files.
        [==================================================] 100%
        3 of 3 items
        ... completed

        Making files available via web.
        [-]
        ... completed


        Task Succeeded

Create an empty repo with a git URL. Use the full URL path to the Dockerfile.::

        $ ./registry-admin.py create aweiteka/webserver --git-url http://git.example.com/repo/myapp
        Repository [aweiteka-webserver] successfully created

Linking a Dockerfile repository with the registry image provides the necessary link for continuous integration workflows. If an event listener was connected to the Pulp registry, the above command would create an event to start an automated docker build using the Dockerfile.

List repositories::

        $ ./registry-admin.py list repos
        my/app
        aweiteka/webserver

List images in a repository::

        $ ./registry-admin.py list my/app
        511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158
        7b23ea3439e3aceaa35bc33529535b3e52c3cf98672da371d9faa09b2969f47c
        bcc5d0080e78726615e55c0954156e1be584832284c9a6621436feb027ae7845
        c811aee30291a2960fbc5b8c46b8c756b4ad98f0c4d44e79b7c7729f1a35ee20


Registry Management
-------------------

Most registry management is performed using native Pulp commands in the form of ``./registry-admin.py pulp "COMMAND"``. Refer to `pulp-admin documentation <https://pulp-user-guide.readthedocs.org/en/pulp-2.4/admin-client/index.html>`_ for complete usage.

Roles
^^^^^

In the example below, we create two roles: "contributor" and "repo_admin"::

        $ ./registry-admin.py pulp "auth role create --role-id contributor"
        $ ./registry-admin.py pulp "auth role create --role-id repo_admin"

Permissions
^^^^^^^^^^^
Permissions must be assigned to roles to enable access.  See `API documentation <https://pulp-dev-guide.readthedocs.org/en/latest/integration/rest-api/index.html>`_ for paths to resources.

Here we create permissions for the "contributors" role so they can create repositories and upload content but cannot delete repositories::

        $ ./registry-admin.py pulp "auth permission grant --role-id contributor --resource /repositories -o create -o read -o update -o execute"
        $ ./registry-admin.py pulp "auth permission grant --role-id contributor --resource /repositories -o create -o read -o update -o execute"
        $ ./registry-admin.py pulp "auth permission grant --role-id contributor --resource /content/uploads -o create -o update"
        $ ./registry-admin.py pulp "auth permission grant --role-id repo_admin --resource /repositories -o create -o read -o update -o delete -o execute"
        $ ./registry-admin.py pulp "auth permission grant --role-id repo_admin --resource /content/uploads -o create -o update"

Users
^^^^^

Users may be manually created. Alternatively the Pulp server may be connected to an LDAP server. See `authentication` for configuration instructions.

Create a contributor user::

        $ ./registry-admin.py pulp "auth user create --login dev_user --password badpass"
        User [dev_user] successfully created

Create a repository admin user::

        $ ./registry-admin.py pulp "auth user create --login admin_user --password badpass"
        User [admin_user] successfully created

Assign user to role::

        $ ./registry-admin.py pulp "auth role user add --role-id contributor --login dev_user"
        User [dev_user] successfully added to role [contributor]

        $ ./registry-admin.py pulp "auth role user add --role-id repo_admin --login admin_user"
        User [admin_user] successfully added to role [repo_admin]

Test permission assignments.

1) Logout as "admin" user::

        $ ./registry-admin.py logout

2) Login as "dev_user"::

        $ ./registry-admin.py login
        User certificate not found.
        Enter registry username [aweiteka]: dev_user
        Enter registry password: 
        Successfully logged in. Session certificate will expire at Sep  4 21:29:43 2014
        GMT.

3) Ensure dev_user can create, upload and publish a repository. Ensure that dev_user cannot delete repositories or manage users.

.. note:: Users that require access to all pulp administrative commands should be assigned the "super-users" role.


Manage Repositories
^^^^^^^^^^^^^^^^^^^

Sync
++++

Repositories may be synced from a remote source. This enables caching of select public content behind a firewall.::

        $ ./registry-admin.py sync rhel7 https://registry.access.redhat.com
        Repository [rhel7] successfully created

This creates a pulp repository named "rhel7" with the rhel7 images from Red Hat.

Groups
++++++

Create repository group::

        $ ./registry-admin.py pulp "repo group create --group-id baseos"
        Repository Group [baseos] successfully created

Assign repository to group::

        $ ./registry-admin.py pulp "repo group members add --group-id=baseos --repo-id rhel7"
        Successfully added members to repository group [baseos]


Metadata
++++++++

Repositories and repository groups may have notes or key:value pair metadata added. Here we add an "environment" note to a repository::

        $ ./registry-admin.py  pulp "docker repo update --repo-id rhel7 --note environment=test"
        Repository [rhel7] successfully updated


Troubleshooting
---------------

See `Troubleshooting Guide <troubleshooting.rst>`_

**Error: Cannot start container <container_id>: port has already been allocated**

If Docker returns this error but there are no running containers allocating conflicting ports docker may need to be restarted.::

        $ sudo systemctl restart docker

**Stale pulp-admin containers**

The ``--rm`` in the pulp-admin alias should remove every pulp-admin container after it stops. However if the container exits prematurely or there is an error the container may not be removed. This command removes all stopped containers::

        $ sudo docker rm $(docker ps -a -q)


Logging
^^^^^^^

Apache and the Pulp Celery workers log to journald. From the container host use ``journalctl``::

        $ sudo journalctl SYSLOG_IDENTIFIER=pulp + SYSLOG_IDENTIFIER=celery + SYSLOG_IDENTIFIER=httpd

Stop
^^^^

#. Download the stop script::

        $ curl -O https://raw.githubusercontent.com/pulp/pulp_packaging/master/dockerfiles/centos/stop.sh

#. Run the stop script, which will stop and remove all pulp containers. It will
   not stop or remove the db or qpid containers.

