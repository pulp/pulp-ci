FROM pulp/centosbase:latest
MAINTAINER Aaron Weitekamp <aweiteka@redhat.com>

# may not need python-pulp-rpm-common
RUN  yum install -y \
         python-qpid-qmf python-qpid \
         python-pulp-rpm-common && \
     yum clean all

ADD run.sh /run.sh

# Usage: /run.sh worker|beat|resource_manager [<unique_worker_number>]
ENTRYPOINT ["/run.sh"]
