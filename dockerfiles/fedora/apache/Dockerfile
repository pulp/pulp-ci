FROM fedora:20
MAINTAINER Mark Lamourine <markllama@gmail.com>

COMMENT { "description": "Pulp apache server image", \ 
          "usage": "docker run -d -p 443:443 --privileged -v /dev/log:/dev/log --volumes-from pulp-data -e APACHE_HOSTNAME=`hostname` pulp/apache" }

ENV container docker

VOLUME [ "/etc/pulp", "/var/www", "/var/lib/pulp" ]

WORKDIR /usr/share/httpd

# Install the base apache requirements
RUN    yum install -y  httpd mod_ssl openssl yum-utils ; yum clean all

# Set up the pulp repos
ADD http://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo \
	/etc/yum.repos.d/fedora-pulp.repo
RUN yum-config-manager --disable pulp-v2-stable && \
    yum-config-manager --enable pulp-v2-beta

# Install the qpid AMQP service components
RUN  yum install -y qpid-cpp-server qpid-cpp-server-store \
         python-qpid-qmf python-qpid && \
         yum clean all

# Install the pulp RPMs (for the pulp and pulp admin wsgi services)
RUN yum groupinstall -y pulp-server && \
    yum install -y python-pulp-rpm-common && \
    yum clean all

EXPOSE 443
EXPOSE 80

ADD docker.conf /etc/pulp/vhosts80/docker.conf
#RUN ln -s /var/www/pub/docker/web /var/www/pub/docker/web80

ADD run.sh /run.sh

CMD [ "/run.sh" ]
