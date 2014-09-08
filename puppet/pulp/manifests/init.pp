# This file is only provided because some tools expect an init.pp
# file to be present. Use pulp::server, pulp::node, or pulp::consumer
# to configure Pulp.
class pulp {
    fail('Please use pulp::server, pulp::node, or pulp::consumer')
}
