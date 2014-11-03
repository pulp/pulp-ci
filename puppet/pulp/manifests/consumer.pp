# Call this class to install, configure, and start a pulp consumer.
# Customize configuration via parameters. For more information see
# the README.md

class pulp::consumer (
    $pulp_server_ca_cert = undef,
    $pulp_server        = $::pulp_server,
    $pulp_port          = 443,
    $pulp_login         = undef,
    $pulp_password      = undef,
    $pulp_api_prefix    = '/pulp/api',
    $pulp_rsa_pub       = '/etc/pki/pulp/consumer/server/rsa_pub.key',
    $verify_ssl         = 'True',
    $ca_path            = '/etc/pki/tls/certs/',
    $id                 = $::hostname,
    $display_name       = $::fqdn,

    # Authentication
    $consumer_rsa_key = '/etc/pki/pulp/consumer/rsa.key',
    $consumer_rsa_pub = '/etc/pki/pulp/consumer/rsa_pub.key',

    # Client role
    $client_role = 'consumer',

    # Filesystem
    $extensions_dir    = '/usr/lib/pulp/consumer/extensions',
    $repo_file         = '/etc/yum.repos.d/pulp.repo',
    $mirror_list_dir   = '/etc/yum.repos.d',
    $gpg_keys_dir      = '/etc/pki/pulp-gpg-keys',
    $cert_dir          = '/etc/pki/pulp/client/repo',
    $id_cert_dir       = '/etc/pki/pulp/consumer/',
    $id_cert_filename  = 'consumer-cert.pem',

    # Reboot
    $reboot       = false,
    $reboot_delay = 3,

    # Logging
    $log_filename      = '~/.pulp/consumer.log',
    $call_log_filename = undef,

    # Output
    $poll_frequency = 1,
    $color_output   = true,
    $wrap_terminal  = false,
    $wrap_width     = 80,

    # Messaging
    $msg_scheme        = 'tcp',
    $msg_host          = $::msg_host,
    $msg_port          = 5672,
    $msg_transport     = rabbitmq,
    $msg_cacert        = undef,
    $msg_clientcert    = undef,

    # Profile
    $profile_minutes = 240,
) inherits pulp::globals {
    # Install, configure, and start the necessary services
    anchor { 'pulp::consumer::start': } ->
    class { 'pulp::consumer::install': } ->
    class { 'pulp::consumer::config': } ->
    class { 'pulp::consumer::service': } ->
    class { 'pulp::consumer::register': } ->
    anchor { 'pulp::consumer::end': }
}

