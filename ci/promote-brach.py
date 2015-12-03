#!/usr/bin/env python2

import os
import subprocess


import argparse
from lib import builder
from lib import promote

current_directory = os.path.realpath(os.path.dirname(__file__))

parser = argparse.ArgumentParser()
description = "Used to promote from one branch to another. For example, from 2.6-dev to " \
              "2.6-testing.  If 2.6-dev is on version 2.6.1-0.2.alpha and 2.6-testing is on " \
              "2.6.0-1 then the end results would be 2.6-dev on 2.6.2-0.1.alpha and " \
              "2.6-testing on 2.2.6.1-0.3.beta"
parser.description = description
parser.add_argument("project_directory",
                    help="The directory containing the project that you want to promote")
parser.add_argument("source_branch", help="The branch that you want to promote from")
parser.add_argument("target_branch", help="The branch that you want to promote to")
parser.add_argument("--remote-name", help="The remote name for the git upstream to use",
                    default='origin')

opts = parser.parse_args()
git_directory = opts.project_directory
source_branch = opts.source_branch
target_branch = opts.target_branch
remote_name = opts.remote_name

print "DANGER ARE YOU SURE YOU WANT TO DO THIS??"
print "All the branches between %s and master will be checked out and pulled." \
      "The results of the promotion will be merged forward to master using '-s ours'."
print "%s and %s will be merged, and updated.  You will be responsible to push to github" % \
      (source_branch, target_branch)
confirmation = raw_input("Are you sure (y/n): ")
if confirmation != 'y':
    print "you thought better, probably a smart move"

print "Checking that we can merge cleanly to master"
# Checkout all the branches required to update & merge forward
promotion_chain = promote.get_promotion_chain(git_directory, target_branch,
                                              upstream_name=remote_name)
promote.check_merge_forward(git_directory, promotion_chain)


print "Getting all the branches required, and pulling the latest version"
for git_branch in promotion_chain:
    promote.checkout_branch(git_directory, git_branch, remote_name=remote_name)

# Update the version on source and merge up
print "Bumping the stage on source before merging to target"
promote.checkout_branch(git_directory, source_branch, remote_name=remote_name)
subprocess.check_call(['./update-version.py', '--update-type', 'stage', git_directory],
                      cwd=current_directory)

new_version = builder.get_nvr_from_spec_file_in_directory(git_directory)
msg = "bumped version to %s" % new_version
subprocess.check_call(['git', 'commit', '-a', '-m', msg], cwd=git_directory)
promote.merge_forward(git_directory)

print "Merging %s into %s " % (source_branch, target_branch)
promote.checkout_branch(git_directory, target_branch, remote_name=remote_name)
subprocess.check_call(['git', 'merge', source_branch], cwd=opts.project_directory)

print "Bumping the patch level on the source branch"
# merge the source into the target branch
promote.checkout_branch(git_directory, source_branch, remote_name=remote_name)
subprocess.check_call(['./update-version.py', '--update-type', 'patch', git_directory],
                      cwd=current_directory)
msg = "bumped version to %s" % new_version
subprocess.check_call(['git', 'commit', '-a', '-m', msg], cwd=git_directory)
promote.merge_forward(git_directory)


print "Don't forget the following branches need to be pushed to github:"
print promotion_chain
