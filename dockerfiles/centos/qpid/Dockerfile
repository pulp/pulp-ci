FROM centos:centos7
MAINTAINER Pulp Team <pulp-list@redhat.com>

RUN yum install -y epel-release && yum clean all

RUN  yum update -y && \
     yum install -y qpid-cpp-server qpid-cpp-server-store python-qpid-qmf python-qpid \
     yum clean all

ADD . /.qpidd

WORKDIR /.qpidd

EXPOSE 5672

ENTRYPOINT ["qpidd", "-t", "--auth=no"]
