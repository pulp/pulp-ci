FROM centos:centos7
MAINTAINER Pulp Team <pulp-list@redhat.com>

ADD rhel-pulp.repo /etc/yum.repos.d/rhel-pulp.repo

RUN yum -d 10 -y install http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-2.noarch.rpm

RUN  yum update -y && \
     yum groupinstall -y \
         pulp-admin && \
     yum install -y \
         pulp-docker-admin-extensions && \
     yum clean all

# config and uploads dir
VOLUME ["/.pulp /run/pulp_uploads"]

ADD admin.conf /root/.pulp/admin.conf
