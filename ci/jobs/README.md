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
