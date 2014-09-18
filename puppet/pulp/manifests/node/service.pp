# This is a private class to configure Pulp node services.

class pulp::node::service {

    service { 'httpd':
        ensure => 'running',
        enable => true
    }

    service { 'goferd':
        ensure => 'running',
        enable => true
    }
}
