# This is is a private class that should not be called directly.
# Use pulp::consumer instead.

class pulp::consumer::register {
      
  if( $pulp::consumer::pulp_login != undef ) and ( $pulp::consumer::pulp_password != undef ) {
    exec { 'pulp-consumer-register':
      command => "/usr/bin/pulp-consumer -u ${pulp::consumer::pulp_login} -p ${pulp::consumer::pulp_password} register --consumer-id ${pulp::consumer::id} --display-name ${pulp::consumer::display_name}",
      unless  => '/usr/bin/pulp-consumer status | /bin/grep "This consumer is registered to the server"',
    }
  }
}
