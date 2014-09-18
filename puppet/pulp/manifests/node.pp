# Call this class to install, configure, and start the Pulp node functionality.
# This requires that the host is already configured as a Pulp server and a Pulp
# consumer registered to its parent Pulp server. For more information on usage,
# see the README.md

class pulp::node (
    $ensure                 = 'installed',
    $ca_path                = '/etc/pki/tls/certs/ca-bundle.crt',
    $node_certificate       = '/etc/pki/pulp/nodes/node.crt',
    $verify_ssl             = 'True',
    $oauth_user_id          = 'admin',
    $parent_oauth_user_id   = 'admin',
    $parent_oauth_key       = undef,
    $parent_oauth_secret    = undef,
){
    class { 'pulp::node::install': } ~>
    class { 'pulp::node::config': } ~>
    class { 'pulp::node::service': }
}

