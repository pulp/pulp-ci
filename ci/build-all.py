#!/usr/bin/env python

import argparse
import yaml
import os
import subprocess
import sys

from lib import builder
from lib.builder import WORKSPACE, TITO_DIR, MASH_DIR, WORKING_DIR


# Parse the args and run the program
parser = argparse.ArgumentParser()
parser.add_argument("config", help="The name of the config file to load from config/releases")
parser.add_argument("--release", action="store_true", default=False,
                    help="Perform a release build. A scratch build will be performed first to "
                         "validate the spec files. ")
parser.add_argument("--disable-push", action="store_true", default=False,
                    help="Don't push to fedorapeople")
parser.add_argument("--rpmsig", help="The rpm signature hash to use when downloading RPMs. "
                                     "Using this flag will cause a failure if any component "
                                     "has not been built already.")
parser.add_argument("--show-versions", action="store_true", default=False,
                    help="Exit after printing out the required versions of each package.")

opts = parser.parse_args()
release_build = opts.release
rpm_signature = opts.rpmsig
# clean the TITO & MASH_DIR
builder.ensure_dir(TITO_DIR, clean=True)
builder.ensure_dir(MASH_DIR, clean=True)
builder.ensure_dir(WORKING_DIR, clean=True)


def load_config(config_name):
    # Get the config
    config_file = os.path.join(os.path.dirname(__file__),
                               'config', 'releases', '%s.yaml' % config_name)
    if not os.path.exists(config_file):
        print "Error: %s not found. " % config_file
        sys.exit(1)
    with open(config_file, 'r') as config_handle:
        config = yaml.safe_load(config_handle)
    return config


def get_components(configuration):
    repos = configuration['repositories']
    for component in repos:
        yield component

builder.init_koji()

# Build our working_dir
working_dir = WORKING_DIR
print working_dir

# load the config
configuration = load_config(opts.config)
koji_prefix = configuration['koji-target-prefix']

# Source extract all the components

print "Getting git repos"
for component in get_components(configuration):
    print "Cloning from github: %s" % component.get('git_url')
    branch_name = component['git_branch']
    command = ['git', 'clone', component.get('git_url'), '--branch', branch_name]
    subprocess.call(command, cwd=working_dir)


print "Building list of downloads & builds"

download_list = []
build_list = []

# Check for external deps
for component in get_components(configuration):
    external_deps_file = component.get('external_deps')
    if external_deps_file:
        external_deps_file = os.path.join(working_dir, component.get('name'), external_deps_file)
        for package_nevra in builder.get_build_names_from_external_deps_file(external_deps_file):
            info = builder.mysession.getBuild(package_nevra)
            if info:
                download_list.extend(builder.get_urls_for_build(builder.mysession, package_nevra))
            else:
                print "External deps requires %s but it could not be found in koji" % package_nevra
                sys.exit(1)

# Get all spec files
for spec in builder.find_all_spec_files(working_dir):
    spec_nvr = builder.get_package_nvr_from_spec(spec)
    package_dists = builder.get_dists_for_spec(spec)
    print "%s %s" % (spec_nvr, package_dists)
    for package_nevra in builder.get_package_nevra(spec_nvr, package_dists):
        info = builder.mysession.getBuild(package_nevra)
        if info:
            download_list.extend(builder.get_urls_for_build(builder.mysession, package_nevra))
        else:
            build_list.append((spec, builder.get_dist_from_koji_build_name(package_nevra)))

# If we are doing a version check, exit here
if opts.show_versions:
    sys.exit(0)

# Sort the list by platform so it is easier to spot missing things in the output
download_list = sorted(download_list, key=lambda download: download[1])

# Perform a scratch build of all the unbuilt packages
build_ids = []

if build_list:
    if rpm_signature:
        print "ERROR: rpm signature specificed but the following releases have not been built."
        for spec, dist in build_list:
            print "%s %s" % (spec, dist)
        sys.exit(1)

    print "Performing koji scratch build "
    for spec, dist in build_list:
        spec_dir = os.path.dirname(spec)
        builder.build_srpm_from_spec(spec_dir, TITO_DIR, testing=True, dist=dist)

    build_ids = builder.build_with_koji(build_tag_prefix=koji_prefix,
                                        srpm_dir=TITO_DIR, scratch=True)
    builder.wait_for_completion(build_ids)

    if release_build:
        print "Performing koji release build"
        # Clean out the tito dir first
        builder.ensure_dir(TITO_DIR)
        spec_dir_set = set()
        for spec, dist in build_list:
            spec_dir = os.path.dirname(spec)
            if spec_dir not in spec_dir_set:
                spec_dir_set.add(spec_dir)
                # Tito tag the new releases
                command = ['tito', 'tag', '--keep-version', '--no-auto-changelog']
                subprocess.check_call(command, cwd=spec_dir)
            builder.build_srpm_from_spec(spec_dir, TITO_DIR, testing=False, dist=dist)

        build_ids = builder.build_with_koji(build_tag_prefix=koji_prefix,
                                            srpm_dir=TITO_DIR, scratch=False)
        builder.wait_for_completion(build_ids)
        for spec_dir in spec_dir_set:
            # Push the tags
            command = ['git', 'push']
            subprocess.check_call(command, cwd=spec_dir)
            command = ['git', 'push', '--tag']
            subprocess.check_call(command, cwd=spec_dir)

print "Downloading rpms"
# Download all the files
builder.download_builds(MASH_DIR, download_list)
builder.download_rpms_from_scratch_tasks(MASH_DIR, build_ids)

print "Building the repositories"
builder.normalize_directories(MASH_DIR)
comps_file = os.path.join(working_dir, 'pulp', 'comps.xml')
builder.build_repositories(MASH_DIR, comps_file=comps_file)

if not opts.disable_push:
    print "Uploading completed repo"
    # Rsync the repos to fedorapeople /srv/repos/pulp/pulp/testing/automation/<rsync-target-dir>
    automation_dir = '/srv/repos/pulp/pulp/testing/automation/'
    target_repo_dir = os.path.join(automation_dir, configuration['rsync-target-dir'])
    command = 'rsync -avze "ssh -o StrictHostKeyChecking=no" ' \
              '--recursive --delete * pulpadmin@repos.fedorapeople.org:%s/' % target_repo_dir
    sys.exit(subprocess.check_call(command, shell=True,  cwd=MASH_DIR))
