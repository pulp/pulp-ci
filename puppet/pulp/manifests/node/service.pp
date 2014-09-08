
class pulp::node::service {
    
    service { 'httpd':
        enable => true,
        ensure => 'running'
    }

    service { 'goferd':
        enable => true,
        ensure => 'running'
    }
}
