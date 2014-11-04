# This is a private class to configure Pulp node services.

class pulp::node::service {

    service { 'goferd':
        ensure => 'running',
        enable => true
    }
}
