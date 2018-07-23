# Pulp Certs

This role creates the CA and sets the SSL certificates for Pulp in Apache and Qpid.

The location of certs is: `/etc/pki`

## Main task

The `main.yml` tasks creates the main CA in `/etc/pki/CA` and sets the certificates for Apache server


## Qpid SSL

The `qpid.yml` tasks creates the qpid NSS database ans sets up the certificates for
broker and client using `certutil` command line.

After the certificates are generated the config files `/etc/qpid/qpidd.conf` and `/etc/pulp/server.conf` are updated with SSL configuration.

After all tasks the services `httpd, pulp_workers, pulp_celerybeat, pulp_resource_maneger and qpidd` are restarted.
