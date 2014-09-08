# This is a private class to install the Pulp node components.

class pulp::node::install {
    package { 'pulp-nodes-child':
        ensure => 'installed'
    }
}
