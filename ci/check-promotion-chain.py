#!/usr/bin/env python2

import os

import argparse
from lib import promote

current_directory = os.path.realpath(os.path.dirname(__file__))

parser = argparse.ArgumentParser()
parser.description = "Used to check if a given branch has been promoted all the way to master. " \
                     "For example, if given 2.5-testing it will check that the chain " \
                     "2.5-testing -> 2.5-dev ->2.6-dev ->master has been merged forward"
parser.add_argument("project_directory",
                    help="The directory containing the project that you want to check")
parser.add_argument("branch", help="The branch that you want to check for promotion")
parser.add_argument("--remote-name", help="The remote name for the git upstream to use",
                    default='origin')

opts = parser.parse_args()
git_directory = opts.project_directory
branch = opts.branch
remote_name = opts.remote_name

# Checkout all the branches required to update & merge forward
promotion_chain = promote.get_promotion_chain(git_directory, branch,
                                              upstream_name=remote_name)
promote.check_merge_forward(git_directory, promotion_chain)

print "%s/%s has already been merged all the way to master." % (remote_name, branch)
