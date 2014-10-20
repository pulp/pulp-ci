# This is a private class that should not be called directly.
#Use pulp::consumer instead

class pulp::consumer::config {
    # Write consumer.conf file
    file { '/etc/pulp/consumer/consumer.conf':
        content => template('pulp/consumer.conf.erb'),
        owner   => 'root',
        group   => 'root',
        mode    => '0644'
    }
}
