FROM pulp/centosbase:latest
MAINTAINER Aaron Weitekamp <aweiteka@redhat.com>

ENV container docker

VOLUME [ "/sys/fs/cgroup" ]

# may not need python-pulp-rpm-common
RUN  yum install -y \
         qpid-cpp-server qpid-cpp-server-store python-qpid-qmf python-qpid \
         python-pulp-rpm-common && \
     yum clean all

RUN yum swap -y -- remove fakesystemd -- install systemd systemd-libs && yum clean all; \
(cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
rm -f /lib/systemd/system/multi-user.target.wants/*;\
rm -f /etc/systemd/system/*.wants/*;\
rm -f /lib/systemd/system/local-fs.target.wants/*; \
rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
rm -f /lib/systemd/system/basic.target.wants/*;\
rm -f /lib/systemd/system/anaconda.target.wants/*; \
systemctl enable httpd.service

EXPOSE 443
EXPOSE 80

ADD docker.conf /etc/pulp/vhosts80/docker.conf
ADD run.sh /run.sh
RUN ln -s /var/www/pub/docker/web /var/www/pub/docker/web80

CMD [ "/run.sh" ]
