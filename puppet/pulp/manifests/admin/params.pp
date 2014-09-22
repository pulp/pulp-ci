# This is a private class that sets the default values for
# the Pulp admin parameters.

class pulp::admin::params inherits pulp::globals {
 
    # /etc/pulp/admin/admin.conf settings #
    #############################################

    # Pulp server
    $pulp_server        = $::pulp_server
    $pulp_port          = 443
    $pulp_api_prefix    = "/pulp/api"
    $pulp_rsa_pub       = "/etc/pki/pulp/consumer/server/rsa_pub.key"
    $verify_ssl         = "True"
    $ca_path            = "/etc/pki/tls/certs/"
    $upload_chunk_size  = "104876"

    # Client role
    $client_role = "admin"

    # Filesystem
    $extensions_dir     = "/usr/lib/pulp/consumer/extensions"
    $repo_file          = "/etc/yum.repos.d/pulp.repo"
    $mirror_list_dir    = "/etc/yum.repos.d"
    $gpg_keys_dir       = "/etc/pki/pulp-gpg-keys"
    $cert_dir           = "/etc/pki/pulp/client/repo"
    $id_cert_dir        = "/etc/pki/pulp/consumer/"
    $id_cert_filename   = "consumer-cert.pem"
    $upload_working_dir = "~/.pulp/uploads"

    # Logging
    $log_filename      = "~/.pulp/consumer.log"
    $call_log_filename = undef

    # Output
    $poll_frequency = 1
    $color_output   = "True"
    $wrap_terminal  = "False"
    $wrap_width     = 80

}
