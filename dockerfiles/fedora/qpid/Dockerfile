FROM fedora:20
MAINTAINER Mark Lamourine <markllama@gmail.com>

#COMMENT { "description": "Qpid server image", \ 
#          "usage": "docker run -d -p 5672:5672 --name pulp-qpid fedora/qpid" }

RUN yum install -y qpid-cpp-server qpid-cpp-server-store python-qpid-qmf python-qpid && \
     yum clean all

ADD . /.qpidd

WORKDIR /.qpidd

EXPOSE 5672

ENTRYPOINT ["/usr/sbin/qpidd", "-t", "--auth=no"]
