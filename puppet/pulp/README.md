# pulp puppet module

####Table of Contents

1. [Overview] (#overview)
2. [Module Description](#module-description)
3. [Setup](#setup)
4. [Usage](#usage)
5. [Reference](#reference)

## Overview

Installs Pulp on RHEL and Fedora from the repository of your choice.

## Module Description

The Pulp module manages pulp server or consumer installation and 
configuration. It does not handle the installation or configuration
of any of its dependencies, which are currently MongoDB and a message
broker for Celery. Current options are Qpid and RabbitMQ. The default
configuration settings for this module are for Qpid. You can make use
of the [MongoDB puppet module](https://forge.puppetlabs.com/puppetlabs/mongodb)
and a Qpid module of your choice to set up these dependencies as necessary.

## Setup

####What this module affects

 * Pulp yum repository.
 * Pulp packages.
 * Pulp configuration files.
 * The httpd, pulp_workers, pulp_celerybeat, and pulp_resource_manager services

###Beginning with Pulp

If you want a server installation of Pulp with the default configuration options
you can run:

```
class {'::pulp::server':}
```

If you need to customize configuration options (which you probably will) you can 
do the following:

```
class {'::pulp::server':
   default_login    => 'jcline',
   default_password => 'hunter2'
}
```

## Usage

Note that Pulp will require a MongoDB server to function properly. By default,
Pulp will attempt to connect to a MongoDB server running on localhost. If you
already have a database available, see the `db_*` parameters for `pulp::server`.
If you don't, you will either need to set one up manually, or use
[puppetlabs/mongodb](https://forge.puppetlabs.com/puppetlabs/mongodb). Pulp also
expects a message broker to be installed. You can use either Qpid or RabbitMQ. By
default, Pulp uses Qpid.

### Install and set up a Pulp server from the beta repository

To install pulp from a different repository (here we use the Pulp beta repository)
you will need to use the `pulp::globals` class:

```puppet
class {'::pulp::globals':
    repo_descr => 'Pulp Beta Repository',
    repo_baseurl => 'http://repos.fedorapeople.org/repos/pulp/pulp/beta/2.4/',
} ->
class {'::pulp::server': }
```

### Create a pulp repo

With the custom pulp_repo type you can specify puppet or rpm repos (rpm default)
 to sync.

```puppet
class pulp::repo::epel_6 {
     pulp_repo { 'epel-6-x86_64':    
       # Default pulp admin login/password
       ensure       => 'present', 
       repo_type    => 'rpm',
       login        => 'admin',
       password     => 'admin',
       display_name => 'epel 6 repo',
       description  => 'epel 6 mirror',
       feed         => 'http://download.fedoraproject.org/pub/epel/6/x86_64',
       schedules    => '2012-12-16T00:00Z/P1D',
       serve_http   => true,
       serve_https  => true,
     }
 }
```

You can also sync secure Red Hat repos with a valid customer cert and key. Make 
sure you subscribe and attach to the correct pool before using the cert/key.

```puppet
class pulp::repo::rhel_6_server {
    pulp_repo { 'rhel-6-server-rpms':
      # Default pulp admin login/password
      ensure       => 'present',
      display_name => 'Red Hat Enterprise Linux 6 Server (RPMs)',
      feed         => 'https://cdn.redhat.com/content/dist/rhel/server/6/6Server/x86_64/os',
      relative_url => 'dist/rhel/server/6/6Server/x86_64/os',
      feed_ca_cert => '/etc/rhsm/ca/redhat-uep.pem',
      feed_cert    => '/etc/pki/entitlement/000000000000000.pem
      feed_key     => '/etc/pki/entitlement/000000000000000-key.pem',
      schedules    => '2012-12-16T02:00Z/P1D',
      serve_http   => false,
      serve_https  => true,
    }
}

```
Puppet repos can be mirrored as well.

```puppet
class pulp::repo::puppet_forge {
    pulp_repo {'puppet_forge':
        ensure       => 'present',
        repo_type    => 'puppet',
        display_name => 'puppet forge',
        description  => "This is a mirror",
        feed         => 'http://forge.puppetlabs.com',
        queries      => ['query1', 'query2'],
        schedules    => [ '2012-12-16T00:00Z/P1D', '2012-12-17T00:00Z/P1D' ],
        serve_http   => true,
        serve_https  => true,
        notes        => {
          'note1' => 'value 1',
          'note2' => 'value 2'
    }
} 
```

Now you can have all the repos set up on a node with

```puppet
node pulp-server {
    include pulp::server
    include pulp::admin
    include pulp::repo::puppet_forge
    include pulp::repo::rhel_6_server
    include pulp::repo::epel_6
    }
```

## Reference

### Classes

####Public classes
* `pulp::globals`: Configure settings that are not server/consumer specific.
* `pulp::server`: Installs and configures a Pulp server
* `pulp::consumer`: Installs and configures a Pulp consumer

####Private classes
* `pulp::params`: Provides a location to set default parameters for Pulp that can be overridden
* `pulp::server::config`: Manages the configuration of a Pulp server
* `pulp::server::install`: Manages the installation of the Pulp server packages
* `pulp::server::service`: Manages the services necessary for a Pulp server
* `pulp::consumer::config`: Manages the configuration of a Pulp consumer
* `pulp::consumer::install`: Manages the installation of the Pulp consumer packages
* `pulp::consumer::service`: Manages the services necessary for a Pulp consumer

####Class: pulp::globals

This class allows you to override what repository the Pulp packages come from.
This is useful if you would like to install the Pulp beta. For more information
on these settings, see the repository options section of the yum.conf manual page.

####`repo_name`
This setting is used to change the repository file name Puppet adds to `/etc/yum.repos.d/`.
The default is 'pulp'.

####`repo_descr`
This setting is used to change the repository description. This is equivalent to the
`name` field in a yum .repo file. The default is 'Pulp Stable Repository'.

####`repo_baseurl`
This is the base URL for the repository. This is *not* equivalent to the `baseurl` field
in a .repo file. It should not include the distribution or architecture. Puppet will
determine these and apply them to the URL. For example: to install the latest 2.4 beta,
you should use the value `http://repos.fedorapeople.org/repos/pulp/pulp/beta/2.4/`.
The default is `http://repos.fedorapeople.org/repos/pulp/pulp/stable/2/`.

####`repo_enabled`
This determines whether the repository is enabled or not. The value should be either
'1' or '0'. The default is '1'.

####`repo_gpgcheck`
This setting is used to determine whether or not to use GPG checking for the repository.
the value should be either '1' or '0'. The default is '0'.

####Class: pulp::server

Most of these parameters manipulate the /etc/pulp/server.conf file.

For more details about the configuration parameters, take a look at the default
configuration file, which is documented in-line.

####`node_parent`
If `true`, the Pulp Nodes Parent package group will be installed. This requires that
OAuth is enabled and configured.

####`enable_celerybeat`
This setting can be used to enable the `pulp_celerybeat` service on this server.
See the server [installation documents](https://pulp-user-guide.readthedocs.org/en/latest/installation.html#server)
for more information. Options are `true` or `false`. The default is `true`.

####`enable_resource_manager`
This setting can be used to enable the `pulp_resource_manager` service on this server.
See the server [installation documents](https://pulp-user-guide.readthedocs.org/en/latest/installation.html#server)
for more information. Options are `true` or `false`. The default is `true`.

####`wsgi_processes`
This setting can be used to change the number of WSGI processes Pulp uses. The default is 3.

####`db_name`
This setting corresponds to the [database] `name` field.

####`db_seed_list`
This setting corresponds to the [database] `seeds` field.

####`db_operation_retries`
This setting corresponds to the [database] `operation_retries` field.

####`db_username`
This setting corresponds to the [database] `username` field.

####`db_password`
This setting corresponds to the [database] `password` field.

####`db_replica_set`
This setting corresponds to the [database] `replica_set` field.

####`server_name`
This setting corresponds to the [server] `server_name` field.

####`server_key_url`
This setting corresponds to the [server] `key_url` field.

####`server_ks_url`
This setting corresponds to the [server] `ks_url` field.

####`default_login`
This setting corresponds to the [server] `default_login` field.

####`default_password`
This setting corresponds to the [server] `default_password` field.

####`debugging_mode`
This setting corresponds to the [server] `debugging_mode` field.

####`log_level`
This setting corresponds to the [server] `log_level` field.

####`auth_rsa_key`
This setting corresponds to the [authentication] `rsa_key` field.

####`auth_rsa_pub`
This setting corresponds to the [authentication] `rsa_pub` field.

####`oauth_enabled`
This boolean setting corresponds to the [oauth] `oauth_enabled` field.
This should be `true` if this server is a parent node. Default is `false`

####`oauth_key`
This setting corresponds to the [oauth] `oauth_key` field.

####`oauth_secret`
This setting corresponds to the [oauth] `oauth_secret` field.

####`cacert`
This setting corresponds to the [security] `cacert` field.

####`cakey`
This setting corresponds to the [security] `cakey` field.

####`ssl_ca_cert`
This setting corresponds to the [security] `ssl_ca_cert` field.

####`user_cert_expiration`
This setting corresponds to the [security] `user_cert_expiration` field.

####`consumer_cert_expiration`
This setting corresponds to the [security] `consumer_cert_expiration` field.

####`serial_number_path`
This setting corresponds to the [security] `serial_number_path` field.

####`consumer_history_lifetime`
This setting corresponds to the [consumer_history] `lifetime` field.

####`reaper_interval`
This setting corresponds to the [data_reaping] `reaper_interval` field.

####`reap_archived_calls`
This setting corresponds to the [data_reaping] `archived_calls` field.

####`reap_consumer_history`
This setting corresponds to the [data_reaping] `consumer_history` field.

####`reap_repo_sync_history`
This setting corresponds to the [data_reaping] `repo_sync_history` field.

####`reap_repo_publish_history`
This setting corresponds to the [data_reaping] `repo_publish_history` field.

####`reap_repo_group_publish_history`
This setting corresponds to the [data_reaping] `repo_group_publish_history` field.

####`reap_task_status_history`
This setting corresponds to the [data_reaping] `task_status_history` field.

####`reap_task_result_history`
This setting corresponds to the [data_reaping] `task_result_history` field.

####`msg_url`
This setting corresponds to the [messaging] `url` field.

####`msg_transport`
This setting corresponds to the [messaging] `transport` field.

####`msg_auth_enabled`
This setting corresponds to the [messaging] `auth_enabled` field.

####`msg_cacert`
This setting corresponds to the [messaging] `cacert` field.

####`msg_clientcert`
This setting corresponds to the [messaging] `clientcert` field.

####`msg_topic_exchange`
This setting corresponds to the [messaging] `topic_exchange` field.

####`tasks_broker_url`
This setting corresponds to the [tasks] `broker_url` field.

####`celery_require_ssl`
This setting corresponds to the [tasks] `celery_require_ssl` field.

####`tasks_cacert`
This setting corresponds to the [tasks] `cacert` field.

####`tasks_keyfile`
This setting corresponds to the [tasks] `keyfile` field.

####`tasks_certfile`
This setting corresponds to the [tasks] `certfile` field.

####`email_host`
This setting corresponds to the [email] `host` field.

####`email_port`
This setting corresponds to the [email] `port` field.

####`email_from`
This setting corresponds to the [email] `from` field.

####`email_enabled`
This setting corresponds to the [email] `enabled` field.

####Class: pulp::consumer

Most of the parameters manipulate the /etc/pulp/consumer/consumer.conf file.

For more details about the configuration parameters, see the
[consumer client installation](https://pulp-user-guide.readthedocs.org/en/latest/installation.html#consumer-client-and-agent)
documentation, and look at the default configuration file, which is documented in-line.

####`pulp_server`
This setting corresponds to the [server] `host` field.

####`pulp_port`
This setting corresponds to the [server] `port` field.

####`pulp_login`
This setting corresponds to the login user for the pulp server

####`pulp_password`
This setting corresponds to the login password for the pulp server

####`pulp_api_prefix`
This setting corresponds to the [server] `api_prefix` field.

####`pulp_rsa_pub`
This setting corresponds to the [server] `rsa_pub` field.

####`verify_ssl`
This setting corresponds to the [server] `verify_ssl` field. The default
is `True`.

####`ca_path`
This setting corresponds to the [server] `ca_path` field. The default
is `/etc/pki/tls/certs/`

####`id`
This setting corresponds to the id of the consumer. The default is its hostname.

####`display_name`
This setting corresponds to the name of the consumer. The default is its fqdn.

####`consumer_rsa_key`
This setting corresponds to the [authentication] `rsa_key` field.

####`consumer_rsa_pub`
This setting corresponds to the [authentication] `rsa_pub` field.

####`client_role`
This setting corresponds to the [client] `role` field.

####`extensions_dir`
This setting corresponds to the [filesystem] `extensions_dir` field.

####`repo_file`
This setting corresponds to the [filesystem] `repo_file` field.

####`mirror_list_dir`
This setting corresponds to the [filesystem] `mirror_list_dir` field.

####`gpg_keys_dir`
This setting corresponds to the [filesystem] `gpg_keys_dir` field.

####`cert_dir`
This setting corresponds to the [filesystem] `cert_dir` field.

####`id_cert_dir`
This setting corresponds to the [filesystem] `id_cert_dir` field.

####`id_cert_filename`
This setting corresponds to the [filesystem] `id_cert_filename` field.

####`reboot`
This setting corresponds to the [reboot] `permit` field.

####`reboot_delay`
This setting corresponds to the [reboot] `delay` field.

####`log_filename`
This setting corresponds to the [logging] `log_filename` field.

####`call_log_filename`
This setting corresponds to the [logging] `call_log_filename` field.

####`poll_frequency`
This setting corresponds to the [output] `poll_frequency` field.

####`color_output`
This setting corresponds to the [output] `color_output` field.

####`wrap_terminal`
This setting corresponds to the [output] `wrap_terminal` field.

####`wrap_width`
This setting corresponds to the [output] `wrap_width` field.

####`msg_scheme`
This setting corresponds to the [messaging] `msg_scheme` field.

####`msg_host`
This setting corresponds to the [messaging] `msg_host` field.

####`msg_transport`
This setting corresponds to the [messaging] `msg_transport` field.

####`msg_cacert`
This setting corresponds to the [messaging] `msg_cacert` field.

####`msg_clientcert`
This setting corresponds to the [messaging] `msg_clientcert` field.

####`profile_minutes`
This setting corresponds to the [profile] `profile_minutes` field.

####pulp_repo
These settings apply to pulp_repo types and hosted repos.

####`id`
The repo-id field of the repository. must be unique. Does not need to be specified manually.

####`ensure`
Required and can be the standard puppet defaults.

####`repo_type`
Specifies the content type. Currently supports values rpm and puppet.
Default value is rpm

####`display_name`
Display name of the repository.

####`description`
Description of the repository.

####`feed`
URL feed of the source of the repository.

####`notes`
Repository notes.

####`validate`
Will validate files upon syncing. Takes a lot of time.

####`queries`
Used for puppet repositories.

####`schedules`
Specify schedules (UTC timezone) for when the repository should sync.

####`serve_https`
Specify that the repo should be published to https link after sync.
Default is true.

####`serve_http`
Sepcify that the repo should be published to http link after sync.
default is false.

####`relative_url`
URL to publish the repository assuming server_http(s) is enabled.

####`feed_ca_cert`
Used for secure repos. Will verify CA cert of feed url.

####`feed_cert`
Certificate used for secure repositories in .pem format.

####`feed_cert`
Key file used to authenticate access to feed in -key.pem format.

####`verify_ssl`
Check SSL of the feed url host.

####`login`
Username to use for pulp-admin commands.
Defaults to admin

####`password`
Password to use for pulp-admin commands.
Defaults to admin
