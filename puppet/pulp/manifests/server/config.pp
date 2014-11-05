# This is a private class that handles Pulp server configuration.

class pulp::server::config {
    # Write server.conf file
    file { '/etc/pulp/server.conf':
        content => template('pulp/server.conf.erb'),
        owner   => 'root',
        group   => 'apache',
        mode    => '0640'
    } -> exec { 'Migrate DB':
        command => '/usr/bin/pulp-manage-db && touch /var/lib/pulp/.puppet-pulp-manage-db',
        user    => 'apache',
        creates => '/var/lib/pulp/.puppet-pulp-manage-db'
    }

    # Configure Apache
    if $pulp::server::wsgi_processes {
        augeas { 'WSGI processes':
            changes => "set /files/etc/httpd/conf.d/pulp.conf/*[self::directive='WSGIDaemonProcess']/arg[4] processes=${pulp::server::wsgi_processes}",
        }
    }
}
