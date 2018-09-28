#!/bin/bash

sudo yum -y install qemu-img yum-utils

# Installing openstack dependencies
# These dependencies are required for building an
# image in openstack.
pip install python-novaclient
pip install python-cinderclient
pip install python-glanceclient
pip install python-keystoneclient
pip install python-neutronclient
pip install python-swiftclient
pip install python-openstackclient

# Installing the disk_image_builder
pip install diskimage-builder

