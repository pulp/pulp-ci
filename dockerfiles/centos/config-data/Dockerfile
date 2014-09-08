FROM aweiteka/pulp-centosbase:latest
MAINTAINER Aaron Weitekamp <aweiteka@redhat.com>

VOLUME [ "/etc/pulp", "/var/www", "/opt/pulp_docker", "/var/lib/pulp" ]

ADD ./run.sh /run.sh

CMD [ "/run.sh" ]
