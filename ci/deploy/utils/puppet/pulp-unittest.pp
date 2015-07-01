# This manifest configures a jenkins node for running the unit tests

class pulp_unittest {
    include stdlib

    $base_packages = [
        'redhat-lsb',
        'wget'
    ]
    package { $base_packages:
        ensure => 'installed'
    }

    if ($::operatingsystem == 'RedHat' or $::operatingsystem == 'CentOS')
        and $::lsbmajdistrelease == 5 {
        # Get the latest puppet verson from puppetlabs. This should pull in
        # the json ruby gem for facter to use.
        $el5_packages = [
            'git',
            'ruby-devel',
            'rubygems',
            'puppet',
            'python-qpid',
            'python-setuptools',
            'python-nose',
            'python-ctypes',
            'python-argparse'
        ]

        package { $el5_packages:
            ensure => 'installed'
        } -> exec { 'install pip':
            # This depends on the el5_packages because python-setuptools must be installed before this step
            command => '/usr/bin/curl -O https://pypi.python.org/packages/source/p/pip/pip-1.1.tar.gz && /bin/tar xfz pip-1.1.tar.gz && pushd pip-1.1 && /usr/bin/python setup.py install && popd && rm -rf pip-*'
        } -> exec { 'install pip deps rhel5':
            # This depends on the el5_packages because python-setuptools must be installed before this step
            command => 'sudo pip install mock>=1.0.1, coverage==3.7, nosexcover==1.0.8',
            path => "/usr/local/bin/:/bin/:/usr/bin/"

        }
    } elsif ($::operatingsystem == 'RedHat' or $::operatingsystem == 'CentOS')
        and $::lsbmajdistrelease == 6 {
        # Qpid is provided by Pulp, so don't install it right now. Also update
        # to the latest Puppet version from puppetlabs
        $el6_packages = [
            'gcc',
            'git',
            'python-devel',
            'ruby-devel',
            'rubygems',
            'puppet',
            'python-pip',
            'python-argparse',
            'python-virtualenvwrapper',
            'tito', 'rpm-build', 'python-paste',  'python-lxml'
        ]

        package { $el6_packages:
            ensure => 'installed'
        } -> exec { 'gem install json':
            command => '/usr/bin/gem install json'
        }

        # RHEL 6.6 apparently doesn't create the mongodb user
        user { "mongodb":
            ensure => "present"
        }
        ->
        class {'::mongodb::server':
        }
        class {'::mongodb::client':}
    } else {
        $packages_qpid = [
            'gcc',
            'git',
            'python-devel',
            'python-pip',
            'python-qpid',
            'python-qpid-qmf',
            'qpid-cpp-server-store',
            'python-virtualenvwrapper',
            # Other non-qpid packages
            'tito', 'rpm-build', 'python-paste',  'python-lxml'
        ]

        package { $packages_qpid:
            ensure => 'installed'
        }

        if ($::operatingsystem == 'RedHat' or $::operatingsystem == 'CentOS')
          and $::lsbmajdistrelease == 7 {
            class {'::mongodb::server':
              pidfilepath => '/var/run/mongodb/mongod.pid',
              smallfiles => true
            }
        } else {
          class {'::mongodb::server':}
        }
        class {'::mongodb::client':}

        class {'::qpid::server':
            config_file => '/etc/qpid/qpidd.conf',
            auth => 'no'
        }
    }
}

include pulp_unittest
