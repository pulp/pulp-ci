FROM fedora:20
MAINTAINER Mark Lamourine <markllama@gmail.com>

# Pulp uses syslog.  All derivative containers must mount /dev/log

ADD https://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo \
	/etc/yum.repos.d/fedora-pulp.repo

RUN yum groupinstall -y pulp-server && \
    yum install -y python-qpid-qmf python-qpid python-pulp-rpm-common && \
    yum install -y augeas && \
    yum clean all

# install pulp_docker plugin to manage docker image repositories
#RUN git clone https://github.com/pulp/pulp_docker.git /opt/pulp_docker
#RUN /opt/pulp_docker/manage_setup_pys.sh develop
#RUN python /opt/pulp_docker/pulp-dev.py -I

# Add an Augeas lens for managing Pulp INI files
ADD pulpini.aug /usr/share/augeas/lenses/dist/pulpini.aug

# Set the service parameters from the ENV inputs
ADD configure_pulp_server.sh /configure_pulp_server.sh

# A script to verify that the MongoDB server is available before attempting
# to start the pulp services that will consume it (and fail if it's not there)
ADD test_db_available.py /test_db_available.py

