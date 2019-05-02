jenkins-user-add
=========

Add the jenkins ci-user on a targeted system.

The definition for the user to be created is defined in `./defaults`

The `.ssh` directory information is kept in an ansible-vault.

This role is intended and designed to be used with Pulp QE ci and Jenkins.

When executed, this role will do the following:

1. Create the `jenkins` group.
2. Create the `jenkins` user.
3. Create the `jenkins` .ssh/ directory.
4. Add `authorized_keys` from the ansible-vault.
5. Add `jenkins` private keys into the .ssh/ directory for rsync.
6. Verify sub-sudoers directories can be created in /etc/sudoers.
7. Add `jenkins` to the /etc/sudoers.d/jenkins file.

Sample usage within a playbook:

```yaml
- hosts: all
  roles:
    - role: jenkins-user-add
```
