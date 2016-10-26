#!/usr/bin/env python2
"""Nightly build promoter.

Block until a decision can be made to promote a nightly build to its tested location. Once the
decision is made to promote the build, copy the built packages from their staging location to
their tested location, as determined by the release config named on the command line.

If promotion is blocked for any reason, "Promotion blocked" will be printed to stdout.
Jenkins can use that text to differentiate job failures (red ball/failure) from promotion
criteria no being met (yellow ball/unstable). This makes it easy for folks looking at the
job to know if the job itself worked and decided not to promote a build, or if the job is
broken and needs developer attention.

"""
from __future__ import print_function

import argparse
import os
import subprocess
import sys
import warnings
from time import sleep

import requests

from lib import builder

JENKINS_API_URL = 'https://pulp-jenkins.rhev-ci-vms.eng.rdu2.redhat.com/api/json'
JENKINS_JOB_API_TPL = ('https://pulp-jenkins.rhev-ci-vms.eng.rdu2.redhat.com/'
                       'job/{name}/lastBuild/api/json')
UPLOAD_BASE_DIR = '/srv/repos/pulp/pulp/testing/automation/'

# suppress warnings to keep the output clean
warnings.simplefilter("ignore")


def main():
    """Parse arguments and return an exit code (e.g. 0 for success, >=1 for failure)"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config', help='The name of the release config file to load')
    parser.add_argument('--job-prefix', action='append', dest='prefixes',
                        help='Prefix of jobs to wait to finish and succeed before promoting, '
                        'can be specified multiple times')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Run remote rsync as a dry-run, not making any actual changes.')
    parser.add_argument('--force', action='store_true', default=False,
                        help='Force promotion, ignoring ')

    opts = parser.parse_args()
    configuration = builder.load_config(opts.config)
    # These must exist in the release config, KeyError here if they don't.
    repo_source_dir = configuration['rsync-target-dir']
    repo_tested_dir = configuration['rsync-tested-dir']

    if opts.force:
        print('Force specified, skipping promotion checks and immediately promoting build.')
    else:
        # We've only got the one check function now,
        # but we should easily be able to add more here if we want to
        for check_func in [job_status_check]:
            print("Running check function: {}".format(check_func.__name__))
            if not check_func(opts.prefixes):
                print("Promotion blocked by check function.")
                # Returning 0 here, since this is a "normal" script exit. Jenkins scripting
                # can be used to parse the output and change the build to Unstable, if desired,
                # based on the printing of this message, as mentioned in the script's docstring.
                return 0

    # Rsync the repos from the source dir to the target dir
    # source dir trailing slash is needed: it ensures that the *contents* of the
    # source dir are copied into the destination dir, not the source dir itself
    remote_source_dir = os.path.join(UPLOAD_BASE_DIR, repo_source_dir) + os.sep
    remote_tested_dir = os.path.join(UPLOAD_BASE_DIR, repo_tested_dir)

    # instead of rsyncing from the local mash to the target dir like build-all does, rsync from
    # the remote target dir to the remote tested dir
    command = ("ssh -o StrictHostKeyChecking=no pulpadmin@repos.fedorapeople.org"
               " rsync -avz --recursive --delete %s %s") % (remote_source_dir, remote_tested_dir)

    if opts.dry_run:
        print("Simulating promotion of {} repo from {} to {}".format(
            opts.config, repo_source_dir, repo_tested_dir))
        command += ' --dry-run'
    else:
        print("Promoting {} repo from {} to {}".format(
            opts.config, repo_source_dir, repo_tested_dir))

    # Finally, return the rsync exit code, so this fails if rsync fails
    return subprocess.check_call(command, shell=True)


def job_status_check(job_prefixes):
    if not job_prefixes:
        # short out if no prefixes to check
        print('No job prefixes to check, skipping job status check step')
        return True

    jobs = []
    for job in requests.get(JENKINS_API_URL, verify=False).json()['jobs']:
        for prefix in job_prefixes:
            if job['name'].startswith(prefix):
                jobs.append(job['name'])

    if not jobs:
        print('No jobs match job prefixes.')
        return False

    print('Checking status of jobs', ', '.join(jobs))

    # Block while a jobs are building. If a job is *not* building, assume it has finished since the
    # previous loop. If it is successful, remove it from the jobs list. If it is not successful,
    # immediately exit: All jobs must be successful to proceed.
    while jobs:
        for job in jobs:
            job_url = JENKINS_JOB_API_TPL.format(name=job)
            try:
                job_status = requests.get(job_url, verify=False).json()
            except ValueError:
                # Not sure why this happens; it's as though the job doesn't exist, but we built the
                # job URL based on the list of jobs that jenkins provides and can be reasonably sure
                # that it does exist. When encountered, re-running the job appears to solve the
                # problem, so here we'll just pause and retry.
                print('unable to parse job data due to jenkins failure')
                sleep(15)
                continue

            if job_status['building']:
                # job is still building, sleep a bit and try the next --
                # this generally shouldn't happen in jenkins, since this script is triggered by
                # the jenkins join plugin trigger, but is still possible if a repo build job is
                # queued while that same repo build job is currently running for some reason, or
                # if this script is run manually.
                print(job, 'still building, trying next job')
                sleep(15)
                continue
            elif job_status['result'] == 'SUCCESS':
                print(job, 'succeded')
                jobs.remove(job)
                break
            else:
                # result should be one of e.g. aborted, failed, unstable
                print(job, str(job_status['result']).lower())
                # no need to check the other jobs, return here on the first failure
                return False

    # all jobs successful, check passed
    return True

if __name__ == '__main__':
    sys.exit(main())
