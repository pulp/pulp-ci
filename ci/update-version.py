#!/usr/bin/env python
import argparse
import os
import sys

from lib import builder, promote

def parse_args():
    parser = argparse.ArgumentParser(epilog='This script is only usable on Pulp 2 projects.')
    parser.add_argument("directory", help="The directory to search for spec files")
    group = parser.add_mutually_exclusive_group(required=True)
    help_text = ("Specify which part of the version is being updated. "
                 "Whichever part is specified will udpate all the other parts in accordance "
                 " with the version guildelines in the documentation. The version is "
                 "structured as major.minor.patch-release.stage (2.6.3-0.1.alpha). "
                 "If any part is updated the parts below it will be reset. "
                 "stage update 2.6.0-1 -> 2.6.1-0.1.alpha "
                 "stage update 2.6.1-0.3.alpha -> 2.6.1-0.4.beta"
                 "stage update 2.6.1-0.5.rc -> 2.6.1-1"
                 "patch update 2.6.1-1 -> 2.6.2-0.1.alpha")
    group.add_argument("--update-type", choices=['major', 'minor', 'patch', 'release', 'stage'],
                       help=help_text)
    group.add_argument("--version", help="Manually set full version (eg. 2.6.2-0.1.alpha)")

    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()

    # version and update_type are mutually exclusive and required
    # if one is not set, the other must be
    if opts.version:
        # user specified version so get it from there
        version, release = promote.split_version(opts.version)
    else:
        raise Exception("Must specify version")

    promote.update_versions(opts.directory, version, release)
