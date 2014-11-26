class jenkins_node_setup(){
  user { "jenkins":
    ensure     => "present",
    managehome => true,
    groups => 'wheel',
  }
  ssh_authorized_key { 'pulp_key.pub':
    user => 'jenkins',
    type => 'ssh-rsa',
    key  => 'AAAAB3NzaC1yc2EAAAADAQABAAABAQC6DJ8fmd61DWPCMiOEuy96ajI7rL3rWu7C9NQhE9a4SfyaiBcghREHJNCz9LGJ57jtOmNV0+UEDhyvTckZI2YQeDqGCP/xO9B+5gQNlyGZ9gSmFz+68NhYQ0vRekikpb9jNdy6ZZbfZDLp1w7dxqDIKfoyu7QO3Qr3E/9CpiucQif2p+oQOVOCdKEjvGYNkYQks0jVTYNRscgmcezpfLKhqWzAre5+JaMB0kRD5Nqadm2uXKZ4cNYStrpZ4xUrnMvAqjormxW2VJNx+0716Wc2Byhg8Nva+bsOkxp/GewBWHfNPtzQGMsL7oYZPtOd/LrmyYeu/M5Uz7/6QCv4N90P',
  }

  exec { 'configure_sudo_tty_access':
    command => "sed -i 's|Defaults[ ]*requiretty|#Defaults    requiretty|g' /etc/sudoers",
    path    => "/usr/local/bin/:/bin/",
  }

  class { 'sudo':
    purge               => false,
    config_file_replace => false,
  }
  sudo::conf { 'jenkins':
    priority => 10,
    content  => "%jenkins ALL=(ALL) NOPASSWD: ALL"
  }
}

include jenkins_node_setup