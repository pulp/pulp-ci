# This is a private clase to configure a pulp node.

class pulp::node::config {
    file { '/etc/pulp/nodes.conf':
        content => template('pulp/nodes.conf.erb'),
        owner   => 'root',
        group   => 'apache',
        mode    => '0640'
    }
}
