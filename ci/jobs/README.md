Jenkins Job Builder
===================

Job Definition Guidelines
-------------------------

When defining jobs in this directory, please organize files according to JJB's recommended layout:

http://docs.openstack.org/infra/system-config/jjb.html#configuring-projects

The summary of what this means:
- Job defaults go in `defaults.yaml`
- Macros go in `macros.yaml`
- Templates go in in files named similarly to the jobs they create so we can easily find them
- Jobs using those templates are defined in `projects.yaml`, and the name of the project should
  match the name of the file containing that project's jobs.

To put it another way, `defaults.yaml`, `macros.yaml` and `projects.yaml` are special files
that must exist. All other yaml files contain jobs, job groups, and job templates. File names
should prefer dashes instead of underscores, preferably not using any underscores at all.

When creating a new build step, always check to see if that build step exists as a macro, or
as a build step in another job. If it already exists as a macro, use the macro. If it already
exists as a build step in another job, turn it into a macro, then use the macro in both jobs.

When creating a new jobs file, remember to make sure a project exists with name of the yaml
file (without the .yaml extension) to ensure that projects.yaml is the definitive place to go
to find out where a job is defined.

When creating a new job template, try not to make the first piece of the job name an expanded
template variable. This is a minor point, but it makes finding the job template used to create
a "real" jenkins job a little bit simpler. Related to this, try to make job names obviously
correspond to their project name, and therefore their yaml file name.

When creating any new definition, please use a descriptive and accurate names so that you don't
necessarily need, for example, to consult a macro definition to know what a macro does.

Job template
------------

The job template `template.yaml.sample` can be used to create new job
definitions. The template defines some required and minial set of options in
order to conform with:

* All jobs should have a owner.
* All owners should receive an email if his/her jobs fail or are not built.
* Before finishing the job the node should be marked offline in order to avoid
  issues with Jenkins reusing a node that is about to be deleted by Nodepool.

To start a new job from the template `cp` it into an YAML file:

    cp template.yaml.sample my-job.yaml

It is suggested to name the file as the name of the job if the new file will
have just one job. Otherwise give the job a meaningful name that describes the
set of jobs that will be defined on the file. Fore more information about job
definition check the previous section.

SSH Agent Configuration
-----------------------

The [Jenkins SSH-Agent Plugin](https://wiki.jenkins-ci.org/display/JENKINS/SSH+Agent+Plugin) allows
the `ssh agent` to be configured with privately stored, secure credentials. The credentials are
installed in the ssh-agent on the machine only during execution.

Add the credential by going to Manage Jenkins -> Manage Credentials and select Add Credential.
Select "SSH Username with private key" and configure as necessary. It is common to enter the key
directly and enter a passphrase using advanced.

Once created, you'll need to find the UUID of the saved credential. From the Jenkins home, select
Credentials -> Global credentials (unrestricted) -> $YOUR_CREDENTIAL. The UUID to use is in the URL
of this page.

Once you have the UUID of interest, add it into your job template. Each job template can define one
or more private credentials to be installed in the `ssh-agent` using the `ssh-agent-credentials`
directive. See the [`ssh-agent-credentials docs`](http://docs.openstack.org/infra/jenkins-job-builder/wrappers.html#wrappers.ssh-agent-credentials)
for examples.

Example Config
--------------

Create the config file.

```sh
mkdir ~/.config/jenkins_jobs/
vi ~/.config/jenkins_jobs/jenkins_jobs.ini
```

Here is an example config:
```ini
[jenkins]
user=bbouters
password=5cxr6230dptzp6l7oqga03chupnqa8f5
url=https://pulp-jenkins.rhev-ci-vms.eng.rdu2.redhat.com
query_plugins_info=False

[job_builder]
include_path=ci/jobs/scripts
```

The password above is your API token. Go to configure page for your username. For example for user
'bbouters' that would be: https://pulp-jenkins.rhev-ci-vms.eng.rdu2.redhat.com/user/bbouters/configure

Click 'Show API Token'.

Example Usage
-------------

Test the potential job changes. Ensure sure you are at the top of the repo.

```sh
jenkins-jobs --ignore-cache test ci/jobs 'docs-builder-*'
```

Update the jobs by job name. Make sure you are at the top of the repo. For example:

```sh
jenkins-jobs --ignore-cache update ci/jobs 'docs-builder-*'
```

Update all jobs. Make sure you are at the top of the repo. For example:

```sh
jenkins-jobs --ignore-cache update ci/jobs
```

SSL Issues
----------

If you don't have the CA that secures our Jenkins instance in your system CA pack JJB will complain
about SSL issues. To fix this add the CA to your system CA pack. Alternatively you can modify the
JJB check to allow insecure usage. Warning: allow ***insecure at your own risk***.

To workaround SSL errors patch line 431 of `/usr/lib/python2.7/site-packages/jenkins/__init__.py`

```python
import ssl
context = ssl._create_unverified_context()
response = urlopen(req, context=context, timeout=self.timeout).read()
```

In my case using the Pulp vagrant environment, the \_\_init\_\_.py file actually lived at:

`/home/vagrant/.virtualenvs/jjb_env/lib/python2.7/site-packages/jenkins/__init__.py`
