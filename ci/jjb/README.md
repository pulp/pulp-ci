# Jenkins

The Pulp project uses Jenkins for some of its testing and docs building. The goal of this guide is
to provide a basic set of instructions to enable Pulp developers to investigate and problems that
may arise with Jenkins, as well as a starting point to build new jobs. Jenkins is a complex
toolset, and it is not within the scope of this guide to document all of it. This guide will help
you to identify and fix problems as well as build new jobs. Much of this guide relies on a
connection
to the Red Hat VPN.

#### Dashboard

The Jenkins Dashboard is the central location for Pulp's Jenkins system. There is a lot of
information on this page, so if you are getting started, there are a few items to pay extra
attention to:
 - Log in. If you are not logged in, you will not have all the available data and options.
 - Jobs List.
   - Order by "Last Triggered" is recommended.
   - Flashing Jobs are currently running
   - The clock with the green "play" button allows you to start this job manually, without
       requiring a hook like "ok test".
 - Build Queue. If your jobs are not running, check the build queue first to make sure that the job
     is being deployed to the queue and isn't held back by other jobs.
 - Build Exectutor Status shows all of the machines and what they are running. If machines are
     offline, they cannot pick up new jobs.

#### Job Page

A job page can be accessed by clicking the job from the dashboard. If your job failed and did not
provide a link to output, this is where you will start. The Console Output shows the output from
the most recent build of this job, and on the left side of the screen is a list of each of the
builds. Clicking on the arrow to the right of each job can provide the console output, parameters,
a restart button, etc.

For debugging, a useful place to check is "Configure" on a Job Page. There, you can see parameters,
configuration, triggers, and the code executed on the box. Warning! Use this page for viewing only,
the jenkins job builder should be used to update.

## Jenkins Job Builder

The Jenkins Job builder is used to build and update all Jenkins jobs, and should be used instead of
manipulating the configuration on the Jenkins web UI.

#### Installation

In a virtual environment, install jenkins job builder with pip:

    pip install jenkins-job-builder

#### Configuration

JJB requires a configuration file to function. It searches for a configuration
file in the following locations, in order:

1. `~/.config/jenkins_jobs/jenkins_jobs.ini`
2. `/etc/jenkins_jobs/jenkins_jobs.ini`

Bootstrap your configuration file:

```sh
install -Dm600 jenkins_jobs.ini ~/.config/jenkins_jobs/jenkins_jobs.ini
vim ~/.config/jenkins_jobs/jenkins_jobs.ini
```

Set your configuration username and password to match the API Token from Jenkins to put into your
configuation file.

On the Jenkins page:
1. Go to your account by clicking your login
1. "Configure"
1. "Show API Token"


For more information, see the [configuration
file](https://docs.openstack.org/infra/jenkins-job-builder/execution.html)
documentation.

##### Configure SSL

Choose one of these options:

__Option 1:__ Add the Jenkins CA in your system CA Pack.

https://mojo.redhat.com/docs/DOC-1122706-configure-ca-cert-in-rhel-and-fedora

__Option 2 (Insecure):__ Workaround Patch

As an alternative to adding the CA, you can workaround the problem by patching the job builder
code in your site-packages.

Assuming you are using a virtual env under `~/.virtualenvs/jjb_env`, replace line 431 of
`~/.virtualenvs/jjb_env/lib/python3.6/site-packages/jenkins/__init__.py` with

```python
import ssl
context = ssl._create_unverified_context()
response = urlopen(req, context=context, timeout=self.timeout).read()
```

This workaround was tested using the following packages versions(in Python 3.6):

 - python-jenkins==0.4.16
 - jenkins-job-builder==2.0.2

#### JJB Usage

The Jenkins Job Builder updates the configuration of jobs on Jenkins to match the jobs locally.
This means that merging to `pulp/pulp-ci` does not automatically update the jobs, and that
Jenkins jobs can be updated before the changes are merged. Generally, it is recommended to update
jobs to test them on Jenkins before merging to the git repo.

Two of the most important things one can do with JJB are to generate jobs and print them to stdout,
and to generate jobs and send them to a Jenkins instance:

```sh
jenkins-jobs test jobs
jenkins-jobs update jobs
```

To update a specific job add the full name:

```sh
jenkins-jobs update ci/jjb/jobs 'unittest-pulp_docker-pr`
```

Or, to update a set of jobs specify a glob:

```sh
jenkins-jobs update ci/jjb/jobs 'unittest*`
```

You can also update a sub-set of jobs, delete jobs, remove outdated jobs, and
more. For more information, start with the [quick start
guide](https://docs.openstack.org/infra/jenkins-job-builder/quick-start.html).

#### Job Definition Guidelines

When defining jobs in this directory, please organize files according to JJB's
[recommended
layout](http://docs.openstack.org/infra/system-config/jjb.html#configuring-projects).
To summarize:

- Job defaults go in `jobs/defaults.yaml`.
- Macros go in `jobs/macros.yaml`.
- Templates go in in files named after to the jobs they create, so they can be
  easily found.
- Jobs using those templates are defined in `jobs/projects.yaml`, and the name
  of the project should match the name of the file containing that project's
  jobs.

To put it another way, `jobs/defaults.yaml`, `jobs/macros.yaml` and
`jobs/projects.yaml` are special files that must exist. All other yaml files
contain jobs, job groups, and job templates. File names should prefer dashes
instead of underscores, preferably not using any underscores at all.

When creating a new build step, always check to see if that build step exists as
a macro, or as a build step in another job. If it already exists as a macro, use
the macro. If it already exists as a build step in another job, turn it into a
macro, then use the macro in both jobs.

When creating a new jobs file, make sure a project exists with name of the yaml
file (without the `.yaml` extension). This ensures that `jobs/projects.yaml` is
the definitive place to go to find out where a job is defined.

When creating a new job template, try not to make the first piece of the job
name an expanded template variable. This is a minor point, but it makes finding
the job template used to create a "real" Jenkins job a little bit simpler.
Related to this, try to make job names obviously correspond to their project
name, and therefore their yaml file name.

When creating any new definition, please use descriptive and accurate names so
that you don't necessarily need, for example, to consult a macro definition to
know what a macro does.

#### Job template

The job template `template.yaml` can be used to create new job definitions. The
template defines some required and minimal set of options:

- All jobs should have a owner.
- All owners should receive an email if his/her jobs fail or are not built.
- Before finishing the job, the node should be marked offline in order to avoid
  issues with Jenkins reusing a node.

To start a new job from the template `cp` it into an YAML file:

```sh
cp template.yaml jobs/my-job.yaml
```

It is suggested to use the job name in the file name if the new file will have
just one job. Otherwise, give the job a meaningful name that describes the set
of jobs that will be defined on the file. For more information about naming
conventions, see the previous section.

## SSH Agent Configuration

The [Jenkins SSH-Agent
Plugin](https://wiki.jenkins-ci.org/display/JENKINS/SSH+Agent+Plugin) allows the
ssh agent to be configured with privately stored, secure credentials. The
credentials are installed in the ssh agent on the machine only during execution.

Add the credential by going to Manage Jenkins → Manage Credentials → Add
Credential. Select "SSH Username with private key" and configure as necessary.
It is common to enter the key directly and enter a passphrase using advanced.

Once created, you'll need to find the UUID of the saved credential. From the
Jenkins home, select Credentials → Global credentials (unrestricted) →
`$YOUR_CREDENTIAL`. The UUID to use is in the URL of this page.

Once you have the UUID of interest, add it into your job template. Each job
template can define one or more private credentials to be installed in the
`ssh-agent` using the `ssh-agent-credentials` directive. See the
[`ssh-agent-credentials`
docs](http://docs.openstack.org/infra/jenkins-job-builder/wrappers.html#wrappers.ssh-agent-credentials)
for examples.
