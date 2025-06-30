pulp-ci
=======

This repository is the home of Pulp's CI files.


## Pulp Project CI Overview

### OCI Images

Nightly: [![Release Image](https://github.com/pulp/pulp-oci-images/actions/workflows/release.yml/badge.svg?event=schedule)](https://github.com/pulp/pulp-oci-images/actions/workflows/release.yml)

Merge: [![Release Image](https://github.com/pulp/pulp-oci-images/actions/workflows/release.yml/badge.svg?event=push)](https://github.com/pulp/pulp-oci-images/actions/workflows/release.yml)

Manual: [![Release Image](https://github.com/pulp/pulp-oci-images/actions/workflows/release.yml/badge.svg?event=workflow_dispatch)](https://github.com/pulp/pulp-oci-images/actions/workflows/release.yml)

### Unified Docs build

[![Publish pulpproject.org](https://github.com/pulp/pulp-docs/actions/workflows/publish.yml/badge.svg)](https://github.com/pulp/pulp-docs/actions/workflows/publish.yml)

Plugin | Nightly | CI Update | CLI
:---|---:|---:|---:
Pulpcore | [![Pulpcore Nightly CI](https://github.com/pulp/pulpcore/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulpcore/actions/workflows/nightly.yml) | [![Pulpcore CI Update](https://github.com/pulp/pulpcore/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulpcore/actions/workflows/update_ci.yml) | [![pulp-cli Nightly](https://github.com/pulp/pulp-cli/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp-cli/actions/workflows/nightly.yml)
Ansible | [![Pulp Ansible Nightly CI](https://github.com/pulp/pulp_ansible/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_ansible/actions/workflows/nightly.yml) | [![Pulp Ansible CI Update](https://github.com/pulp/pulp_ansible/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_ansible/actions/workflows/update_ci.yml) | N/A
Certguard | [![Pulp Certguard Nightly CI](https://github.com/pulp/pulp-certguard/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp-certguard/actions/workflows/nightly.yml) | [![Pulp Certguard CI Update](https://github.com/pulp/pulp-certguard/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp-certguard/actions/workflows/update_ci.yml) | N/A
Container | [![Pulp Container Nightly CI](https://github.com/pulp/pulp_container/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_container/actions/workflows/nightly.yml) | [![Pulp Container CI Update](https://github.com/pulp/pulp_container/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_container/actions/workflows/update_ci.yml) | N/A
Deb | [![Pulp Deb Nightly CI](https://github.com/pulp/pulp_deb/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_deb/actions/workflows/nightly.yml) | [![pULP Deb CI Update](https://github.com/pulp/pulp_deb/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_deb/actions/workflows/update_ci.yml) | [![pulp-cli-deb Nightly](https://github.com/pulp/pulp-cli-deb/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp-cli-deb/actions/workflows/nightly.yml)
File | [![Pulp File Nightly CI](https://github.com/pulp/pulp_file/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_file/actions/workflows/nightly.yml) | [![Pulp File CI Update](https://github.com/pulp/pulp_file/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_file/actions/workflows/update_ci.yml) | N/A
Gem | [![Pulp Gem Nightly CI](https://github.com/pulp/pulp_gem/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_gem/actions/workflows/nightly.yml) | [![Pulp Gem CI Update](https://github.com/pulp/pulp_gem/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_gem/actions/workflows/update_ci.yml) | [![pulp-cli-gem Nightly](https://github.com/pulp/pulp-cli-gem/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp-cli-gem/actions/workflows/nightly.yml)
Maven | [![Pulp Maven Nightly CI](https://github.com/pulp/pulp_maven/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_maven/actions/workflows/nightly.yml) | [![Pulp Maven CI Update](https://github.com/pulp/pulp_maven/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_maven/actions/workflows/update_ci.yml) | [![pulp-cli-maven Nightly](https://github.com/pulp/pulp-cli-maven/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp-cli-maven/actions/workflows/nightly.yml)
NPM | [![Pulp Npm Nightly CI](https://github.com/pulp/pulp_npm/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_npm/actions/workflows/nightly.yml) | [![Pulp Npm CI Update](https://github.com/pulp/pulp_npm/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_npm/actions/workflows/update_ci.yml) | N/A
OSTree | [![Pulp OSTree Nightly CI](https://github.com/pulp/pulp_ostree/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_ostree/actions/workflows/nightly.yml) | [![Pulp OSTree CI Update](https://github.com/pulp/pulp_ostree/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_ostree/actions/workflows/update_ci.yml) | [![pulp-cli-ostree Nightly](https://github.com/pulp/pulp-cli-ostree/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp-cli-ostree/actions/workflows/nightly.yml)
Python | [![Pulp Python Nightly CI](https://github.com/pulp/pulp_python/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_python/actions/workflows/nightly.yml) | [![Pulp Python CI Update](https://github.com/pulp/pulp_python/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_python/actions/workflows/update_ci.yml) | N/A
RPM | [![Pulp Rpm Nightly CI](https://github.com/pulp/pulp_rpm/actions/workflows/nightly.yml/badge.svg)](https://github.com/pulp/pulp_rpm/actions/workflows/nightly.yml) | [![Pulp Rpm CI Update](https://github.com/pulp/pulp_rpm/actions/workflows/update_ci.yml/badge.svg)](https://github.com/pulp/pulp_rpm/actions/workflows/update_ci.yml) | N/A
