
class pulp::node::install {
    package { "pulp-nodes-child":
        ensure => "installed"
    }
}
