FROM centos:centos7
MAINTAINER Aaron Weitekamp <aweiteka@redhat.com>

ADD rhel-pulp.repo /etc/yum.repos.d/rhel-pulp.repo

RUN yum -y install http://dl.fedoraproject.org/pub/epel/beta/7/x86_64/epel-release-7-1.noarch.rpm

RUN yum update -y && \
    yum groupinstall -y pulp-server && \
    yum clean all

ADD pulp-docker-admin-extensions-0.1.1-1.el7sat.noarch.rpm \
    pulp-docker-admin-extensions-0.1.1-1.el7sat.noarch.rpm
ADD pulp-docker-plugins-0.1.1-1.el7sat.noarch.rpm \
    pulp-docker-plugins-0.1.1-1.el7sat.noarch.rpm
ADD python-pulp-docker-common-0.1.1-1.el7sat.noarch.rpm \
    python-pulp-docker-common-0.1.1-1.el7sat.noarch.rpm
RUN yum install -y python-pulp-docker-common-0.1.1-1.el7sat.noarch.rpm \
    pulp-docker-admin-extensions-0.1.1-1.el7sat.noarch.rpm \
    pulp-docker-plugins-0.1.1-1.el7sat.noarch.rpm

