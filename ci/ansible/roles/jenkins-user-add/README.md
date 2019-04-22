jenkins-user-add
=========

Add the jenkins ci-user on a targeted system.

When executed, this role will do the following:

1. Create the `jenkins` group.
2. Create the `jenkins` user.
3. Create the `jenkins` .ssh/ directory.
4. Add `authorized_keys` from the ansible_user's `authorized_keys`
5. Verify sub-sudoers directories can be created in /etc/sudoers.
6. Add `jenkins` to the /etc/sudoers.d/jenkins file

Sample usage within a playbook:

```yaml
- hosts: all
  roles:
    - role: jenkins-user-add
```
