Starting with 2.8, the following naming scheme is in use:

x.y-dev.yaml
============

These release configs are used by the nightly builds of packages
and documentation, and should reflect the next release that would
be built in an x.y stream. The packages should be versioned with
'-0.n.alpha'.

x.y-build.yaml
==============

These release configs are used by the person currently building
packages for Pulp, and during a release cycle will change frequently.
They should reflect the most recently built version of Pulp in a stream,
and be based on the -dev config for that stream. Packages created by
this config should be versioned with '-0.n.beta', '0.n.rc', or indicate
a released version with a release version component of '-1' or higher.

This config is used to build the "dev" documentation for a stream,
representing documentation generated from the most recently tagged
pre-release version in a stream.

-build configs should generally be based on the -dev config of the
same stream, taking care to only increment plugin versions if changes
are present on the x.y-dev branch of that plugin. If no such changes
are present, the plugin's current version and release branch should
be used.

x.y-release.yaml
================

These release configs are used to build the documentation for
previous releases. After a build has been released, the -build
config should be copied over the -release config in the same stream
to ensure correctness of published documentation for a release.
