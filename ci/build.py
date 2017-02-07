#!/usr/bin/env python2

import argparse
import os
import subprocess

from lib import builder
from lib import promote
from lib.builder import WORKING_DIR


parser = argparse.ArgumentParser(
    description="A tool to build the rpms for a single git project in koji. "
                "This does not process external_deps. That is left for the assembly "
                "done by build-all.py"
)

parser.add_argument("project", help="The name of the project to build (pulp, pulp_rpm, crane, ...)")
parser.add_argument("--branch", default="master",
                    help="The branch to build. Defaults to master.")
parser.add_argument("--koji_prefix", default="pulp-2.7",
                    help="The prefix for the koji build taret to use. Defaults to pulp-2.7")
parser.add_argument("--release", action="store_true", default=False,
                    help="Perform a release build. If a release build is requested the "
                         "branch will be verified to be in the form x.y-(dev|testing|release) "
                         "or 'master'. In addition the version will be tagged & the commit "
                         "will be promoted through to master")

opts = parser.parse_args()

builder.ensure_dir(WORKING_DIR, clean=True)
TITO_DIR = os.path.join(WORKING_DIR, 'tito')
MASH_DIR = os.path.join(WORKING_DIR, 'mash')
builder.ensure_dir(TITO_DIR, clean=True)
builder.ensure_dir(MASH_DIR, clean=True)

# Initialize our connection to koji
builder.init_koji()

# Build our WORKING_DIR
builder.ensure_dir(WORKING_DIR, clean=True)

# Get the project to build from git by spoofing a release config component
component = {
    'name': opts.project,
    'git_url': "git@github.com:pulp/{}.git".format(opts.project),
    'git_branch': opts.branch,
}
project_path = builder.clone_branch(component)

print("Building list of things to build")

download_list = []
build_list = []

# Get all spec files
for spec in builder.find_all_spec_files(project_path):
    spec_nvr = builder.get_package_nvr_from_spec(spec)
    package_dists = builder.get_dists_for_spec(spec)
    print("%s %s" % (spec_nvr, package_dists))
    for package_nevra in builder.get_package_nevra(spec_nvr, package_dists):
        info = builder.mysession.getBuild(package_nevra)
        if info:
            download_list.extend(builder.get_urls_for_build(builder.mysession, package_nevra))
        else:
            build_list.append((spec, builder.get_dist_from_koji_build_name(package_nevra)))

# Sort the list by platform so it is easier to spot missing things in the output
download_list = sorted(download_list, key=lambda download: download[1])

# Perform a scratch build of all the unbuilt packages
build_ids = []

if build_list:
    print("Performing koji scratch build")
    for spec, dist in build_list:
        spec_dir = os.path.dirname(spec)
        builder.build_srpm_from_spec(spec_dir, TITO_DIR, testing=True, dist=dist)

    build_ids = builder.build_with_koji(build_tag_prefix=opts.koji_prefix,
                                        srpm_dir=TITO_DIR, scratch=True)
    builder.wait_for_completion(build_ids)

    if opts.release:
        print("Performing koji release build")
        # Clean out the tito dir first
        builder.ensure_dir(TITO_DIR)
        spec_dir_set = set()
        for spec, dist in build_list:
            spec_dir = os.path.dirname(spec)
            if spec_dir not in spec_dir_set:
                spec_dir_set.add(spec_dir)
                # make sure we are clean to merge forward before tagging
                git_branch = promote.get_current_git_upstream_branch(spec_dir)
                parent_branch = component.get('parent_branch', None)
                promotion_chain = promote.get_promotion_chain(
                    spec_dir, git_branch, parent_branch=parent_branch)
                promote.check_merge_forward(spec_dir, promotion_chain)
                # Tito tag the new releases
                command = ['tito', 'tag', '--keep-version', '--no-auto-changelog']
                subprocess.check_call(command, cwd=spec_dir)
            builder.build_srpm_from_spec(spec_dir, TITO_DIR, testing=False, dist=dist)

        build_ids = builder.build_with_koji(build_tag_prefix=opts.koji_prefix,
                                            srpm_dir=TITO_DIR, scratch=False)
        builder.wait_for_completion(build_ids)
        for spec_dir in spec_dir_set:
            # Push the tags
            command = ['git', 'push']
            subprocess.check_call(command, cwd=spec_dir)
            command = ['git', 'push', '--tag']
            subprocess.check_call(command, cwd=spec_dir)

            # Merge merge the commit forward, pushing along the way
            promote.merge_forward(spec_dir, push=True)

print("Downloading rpms")
# Download all the files
builder.download_builds(MASH_DIR, download_list)
builder.download_rpms_from_scratch_tasks(MASH_DIR, build_ids)
