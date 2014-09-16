FROM docker-registry.usersys.redhat.com/markllama/pulp-base

MAINTAINER Mark Lamourine <markllama@gmail.com>

ENV container docker

WORKDIR /usr/share/httpd

VOLUME [ "/var/www", "/var/lib/pulp" ]

EXPOSE 80
EXPOSE 443

ADD docker.conf /etc/pulp/vhosts80/docker.conf
#RUN ln -s /var/www/pub/docker/web /var/www/pub/docker/web80

ADD run.sh /run.sh

CMD [ "/run.sh" ]
