# Call this class to install the pulp-admin client

class pulp::admin (
    $pulp_server                = $::pulp_server,
    $pulp_port                  = 443,
    $pulp_api_prefix            = '/pulp/api',
    $pulp_rsa_pub               = '/etc/pki/pub/admin/server/rsa_pub.key',
    $verify_ssl                 = 'true',
    $ca_path                    = '/etc/pki/tls/certs/ca-bundle.crt',
    $upload_chunk_size          = '1048576',
    $client_role                = 'admin',
    $extensions_dir             = '/usr/lib/pulp/admin/extensions',
    $id_cert_dir                = '~/.pulp/',
    $id_cert_filename           = 'user-cert.pem',
    $upload_working_dir         = '~/.pulp/uploads',
    $log_filename               = '~/.pulp/admin.log',
    $call_log_filename          = undef, #Default = '~/.pulp/server_calls.log'
    $poll_frequency             = '1',
    $color_output               = 'true',
    $wrap_terminal              = 'false',
    $wrap_width                 = 80,
) inherits pulp::globals {
    exec { 'yum install pulp-admin':
        command => '/usr/bin/yum -y groupinstall pulp-admin',
        unless  => '/usr/bin/yum grouplist "Pulp Admin" | /bin/grep -i "^Installed Groups"',
        timeout => 600,
    } ->
    file { '/etc/pulp/admin/admin.conf':
        ensure  => present,
        content => template('pulp/admin.conf.erb'),
        owner   => root,
        group   => root,
        mode    => '0644',
    }
}
    
