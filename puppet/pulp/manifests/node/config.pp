
class pulp::node::config {
    file { '/etc/pulp/nodes.conf':
        content => template('pulp/nodes.conf.erb'),
        owner   => 'root',
        group   => 'apache',
        mode    => '0640'
    }
}
