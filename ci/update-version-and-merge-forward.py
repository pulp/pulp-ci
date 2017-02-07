#!/usr/bin/env python
"""
This script, as indicated by the name, will update the versions stored in a spec file and python
files based on the values in a release config. It is also the easiest way to clone all of the
repositories defined in a given release configuration, including repositories configured to check
out from a tag or branch.

No changes will be made to github unless the --push flag is passed.
"""

import argparse
import yaml
import os
import subprocess
import sys

from lib import builder
from lib import promote
from lib.builder import WORKING_DIR, CI_DIR


def parse_args():
    # Parse the args and run the program
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="The name of the config file to load from config/releases")
    parser.add_argument("--push", action="store_true", default=False,
                        help="Push to GitHub")
    parser.add_argument("--merge-forward-only", action="store_false", default=True,
                        dest="update_version", help="Don't update versions, only merge forward.")
    parser.add_argument("--working-dir", default=WORKING_DIR,
                       help="Working directory, where git clones will be updated.")

    return parser.parse_args()


def update_version_and_merge_for_component(component, opts):
    project_dir = builder.clone_branch(component)

    try:
        git_branch = promote.get_current_git_upstream_branch(project_dir)
        parent_branch = component.get('parent_branch')
    except subprocess.CalledProcessError:
        # most likely, git branch is a tag. In that event, there's nothing to update or
        # merge forward. The script was either called with the wrong release config, or is
        # being used as an expedient to check out the git repos for a given release config.
        # Either way, nothing can be done with this branch.
        print(("Unable to determine git branch for git repo in {}, HEAD is probably a tag."
               " Moving to next component.").format(project_dir))
        return

    if opts.update_version:
        if git_branch.endswith('-release'):
            # Even if update_version was requested, the only way versions should get updated on an
            # x.y-release branch is through the merging of a released tag.
            print("Not updating version on release branch, only merging branches forward.")
        else:
            promotion_chain = promote.get_promotion_chain(project_dir, git_branch,
                                                          parent_branch=parent_branch)
            promote.check_merge_forward(project_dir, promotion_chain)
            update_version = os.path.join(CI_DIR, 'update-version.py')
            # Update the version to the one specified in the config
            command = ['./update-version.py', '--version', component['version'], project_dir]
            subprocess.call(command, cwd=CI_DIR)
            command = ['git', 'commit', '-a', '-m', 'Bumping version to %s' % component['version']]
            subprocess.call(command, cwd=project_dir)
            if opts.push:
                command = ['git', 'push', '-v']
                subprocess.call(command, cwd=project_dir)
    else:
        print("Skipping version update, only merging branches forward.")
    promote.merge_forward(project_dir, push=opts.push, parent_branch=parent_branch)


def main():
    opts = parse_args()

    # Load the config file
    configuration = builder.load_config(opts.config)

    # Ensure the working dir exists
    builder.ensure_dir(WORKING_DIR, clean=True)

    print("Getting git repos")
    for component in builder.components(configuration):
        update_version_and_merge_for_component(component, opts)


if __name__ == '__main__':
    main()
