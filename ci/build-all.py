#!/usr/bin/env python2

import argparse
import os
import subprocess
import sys

from lib import builder
from lib import promote
from lib.builder import WORKSPACE, TITO_DIR, MASH_DIR, WORKING_DIR, CI_DIR


# Parse the args and run the program
parser = argparse.ArgumentParser()
parser.add_argument("config", help="The name of the config file to load from config/releases")
parser.add_argument("--release", action="store_true", default=False,
                    help="Perform a release build. A scratch build will be performed first to "
                         "validate the spec files unless skipped with --skipscratch. ")
parser.add_argument("--skipscratch", action="store_true", default=False,
                    help="When performing a release build, skip the scratch build step.")
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


def get_components(configuration):
    repos = configuration['repositories']
    for component in repos:
        yield component

def project_name_from_spec_dir(spec_dir):
    remainder = spec_dir
    while True:
        remainder, dir_name = os.path.split(remainder)
        for project in component_list:
            if project == dir_name:
                return project
        if remainder == '/':
            return None

builder.init_koji()

# Build our working_dir
working_dir = WORKING_DIR
print working_dir
# Load the config file
configuration = builder.load_config(opts.config)
koji_prefix = configuration['koji-target-prefix']

# Source extract all the components

parent_branches = {}
merge_forward = {}
component_list = []
spec_project_map = {}

print "Getting git repos"
for component in get_components(configuration):
    print "Cloning from github: %s" % component.get('git_url')
    branch_name = component['git_branch']
    parent_branch = component.get('parent_branch', None)
    command = ['git', 'clone', component.get('git_url'), '--branch', branch_name]
    subprocess.call(command, cwd=working_dir)
    parent_branch = component.get('parent_branch', None)
    parent_branches['origin/%s' % branch_name] = parent_branch
    project_dir = os.path.join(working_dir, component['name'])

    # Check if this is a branch or a tag
    tag_exists = builder.does_git_tag_exist(branch_name, project_dir)
    component_list.append(component['name'])
    merge_forward[component['name']] = False
    if not tag_exists:
        merge_forward[component['name']] = True
        # Check if everything is merged forward
        print "Checking that everything is merged forward."
        git_branch = promote.get_current_git_upstream_branch(project_dir)
        promotion_chain = promote.get_promotion_chain(project_dir, git_branch, parent_branch=parent_branch)
        promote.check_merge_forward(project_dir, promotion_chain)

    # Update the version if one is specified in the config
    if 'version' in component:
        command = ['./update-version.py', '--version', component['version'], project_dir]
        subprocess.call(command, cwd=CI_DIR)
        command = ['git', 'commit', '-a', '-m', 'Bumping version to %s' % component['version']]
        subprocess.call(command, cwd=project_dir)

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
                download_list.extend(builder.get_urls_for_build(builder.mysession, package_nevra, rpmsig=rpm_signature))
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
            download_list.extend(builder.get_urls_for_build(builder.mysession, package_nevra, rpmsig=rpm_signature))
        else:
            build_list.append((spec, builder.get_dist_from_koji_build_name(package_nevra)))

# If we are doing a version check, exit here
if opts.show_versions:
    sys.exit(0)

# Match spec files to project


# Sort the list by platform so it is easier to spot missing things in the output
download_list = sorted(download_list, key=lambda download: download[1])

# Perform a scratch build of all the unbuilt packages
build_ids = []

if build_list:
    #import pdb;pdb.set_trace()
    if rpm_signature:
        print "ERROR: rpm signature specificed but the following releases have not been built."
        for spec, dist in build_list:
            print "%s %s" % (spec, dist)
        sys.exit(1)

    if release_build and opts.skipscratch:
        # scratch build can only be skipped for release builds
        print "Skipping koji scratch build for release "
    else:
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
                tag_name = builder.get_package_nvr_from_spec(spec)
                # Don't tag this again if the tag already exists
                if not builder.does_git_tag_exist(
                        builder.get_package_nvr_from_spec(spec), spec_dir):
                    spec_dir_set.add(spec_dir)
                    # Tito tag the new releases
                    command = ['tito', 'tag', '--keep-version', '--accept-auto-changelog']
                    subprocess.check_call(command, cwd=spec_dir)
            builder.build_srpm_from_spec(spec_dir, TITO_DIR, testing=False, dist=dist)

        build_ids = builder.build_with_koji(build_tag_prefix=koji_prefix,
                                            srpm_dir=TITO_DIR, scratch=False)
        builder.wait_for_completion(build_ids)
        for spec_dir in spec_dir_set:
            project_name = None
            project_name = project_name_from_spec_dir(spec_dir)

            # Push the tags
            if merge_forward[project_name]:
                command = ['git', 'push']
                subprocess.check_call(command, cwd=spec_dir)
            command = ['git', 'push', '--tag']
            subprocess.check_call(command, cwd=spec_dir)

            if merge_forward[project_name]:
                # Merge the commit forward, pushing along the way
                git_branch = promote.get_current_git_upstream_branch(spec_dir)
                promote.merge_forward(spec_dir, push=True, parent_branch=parent_branches[git_branch])

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
