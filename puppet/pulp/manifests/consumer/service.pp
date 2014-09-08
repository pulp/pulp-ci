# This is a private class that should never be called directly

class pulp::consumer::service {

    service { 'goferd':
        ensure => 'running',
        enable => true
    }
}
