# This is a private class that should not be called directly.
# Use pulp::server instead.

class pulp::server::install {
    # Not elegant, but Puppet doesn't support yum groups
    exec {
        'yum install pulp-server':
        command => '/usr/bin/yum -y groupinstall "Pulp Server"',
        unless  => '/usr/bin/yum grouplist "Pulp Server" | /bin/grep -i "^Installed Groups"',
        timeout => 600
    }

    if pulp::server::node_parent {
        package { 'pulp-nodes-parent':
            ensure => 'installed'
        }
    }

    Exec['yum install pulp-server'] -> Package['pulp-nodes-parent']
}
