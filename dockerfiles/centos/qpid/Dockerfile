FROM centos:centos7
MAINTAINER Aaron Weitekamp <aweiteka@redhat.com>

RUN yum -y install http://dl.fedoraproject.org/pub/epel/beta/7/x86_64/epel-release-7-0.2.noarch.rpm

RUN  yum update -y && \
     yum install -y qpid-cpp-server qpid-cpp-server-store python-qpid-qmf python-qpid \
     yum clean all

ADD . /.qpidd

WORKDIR /.qpidd

EXPOSE 5672

ENTRYPOINT ["qpidd", "-t", "--auth=no"]
