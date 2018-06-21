pulp-fips
=========

Enable FIPS on a RHEL 7 (or CentOS 7) host.

When executed, this role will do the following:

1. Install packages needed for FIPS support. If needed, generate a new
   initramfs.
2. Make GRUB pass a FIPS-enablement flag to the kernel at boot time. If needed,
   also generate a new GRUB configuration and restart the host.
3. Assert that FIPS is supported and enabled.

No variables are supported. Sample usage within a playbook:

```yaml
- hosts: all
  roles:
    - role: pulp-fips
```
