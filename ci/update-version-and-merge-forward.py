#!/usr/bin/env python

import argparse
import yaml
import os
import subprocess
import sys

from lib import builder
from lib import promote
from lib.builder import WORKSPACE, TITO_DIR, MASH_DIR, WORKING_DIR, CI_DIR


# Parse the args and run the program
parser = argparse.ArgumentParser()
parser.add_argument("config", help="The name of the config file to load from config/releases")
parser.add_argument("--push", action="store_true", default=False,
                    help="Don't push to GitHub")

opts = parser.parse_args()
push_to_github = opts.push
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

# Build our working_dir
working_dir = WORKING_DIR
print working_dir
# Load the config file
configuration = load_config(opts.config)

print "Getting git repos"
for component in get_components(configuration):
    print "Cloning from github: %s" % component.get('git_url')
    branch_name = component['git_branch']
    parent_branch = component.get('parent_branch', None)
    command = ['git', 'clone', component.get('git_url'), '--branch', branch_name]
    subprocess.call(command, cwd=working_dir)
    project_dir = os.path.join(working_dir, component['name'])
    git_branch = promote.get_current_git_upstream_branch(project_dir)
    promotion_chain = promote.get_promotion_chain(project_dir, git_branch, parent_branch=parent_branch)
    promote.check_merge_forward(project_dir, promotion_chain)
    update_version = os.path.join(CI_DIR, 'update-version.py')
    # Update the version to the one specified in the config
    command = ['./update-version.py', '--version', component['version'], project_dir]
    subprocess.call(command, cwd=CI_DIR)
    command = ['git', 'commit', '-a', '-m', 'Bumping version to %s' % component['version']]
    subprocess.call(command, cwd=project_dir)
    promote.merge_forward(project_dir, push=push_to_github, parent_branch=parent_branch) 
