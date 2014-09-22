# Call this class to install the pulp-admin client

class pulp::admin inherits pulp::admin::params {
    exec { 'yum install pulp-admin':
        command => '/usr/bin/yum -y groupinstall pulp-admin',
        unless  => '/usr/bin/yum grouplist "Pulp Admin" | /bin/grep "^Installed groups"',
        timeout => 600,
    }
    file { '/etc/pulp/admin/admin.conf':
        ensure  => present,
        content => template('pulp/admin.conf.erb'),
        owner   => root,
        group   => root,
        mode    => '0644',
    }
}
    
