Nodepool configuration
======================

General Nodepool configuration information can be found at
http://docs.openstack.org/infra/nodepool/

For Pulp's usage of nodepool an assumption is made that nodepool has been
installed with a user named 'nodepool'. As pip install or source install does
not create a systemctl service to start/stop nodepool a service definition is
in this directory 'nodepoold.service'

The nodepool config expects a 'scripts' directory containing the script used to
setup base image for use as nodes. The base script that pulp has been using is
contained here at prepare_node.sh

The nodepool.yaml is a sample and will require significant editing to fill in
the credentials & proper directories on any new nodepool server.

Bootstrap script
----------------

The bootstrap.sh script make sure that the node is able to be registered as a
Jenkins executor.

It expects that some files are available on the scripts directory:

* ``id_rsa.pub``: the Jenkins id_rsa.pub that will be added as ssh authorized
  key to allow Jenkins ssh in the node to set it up as an executor.
* ``rhel*-rcm-internal.repo``: these repo files will be added as the only
  available repositories for RHEL nodes.

Make sure to have the above files in place before running nodepool. If they are
not available the bootstrap script will fail and no image will be generated.
