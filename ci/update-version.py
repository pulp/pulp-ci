#!/usr/bin/env python

import glob
import os
import re
import shutil
from StringIO import StringIO
import sys


import argparse
from lib import builder


def parse_version(version):
    version_components = version.split('.')
    major_version = 0
    minor_version = 0
    patch_version = 0
    try:
        major_version = int(version_components.pop(0))
        minor_version = int(version_components.pop(0))
        patch_version = int(version_components.pop(0))
    except IndexError:
        pass
    return major_version, minor_version, patch_version


def parse_release(release):
    release_components = release.split('.')
    major_release = 0
    minor_release = None
    stage = None
    try:
        major_release = int(release_components.pop(0))
        minor_release = int(release_components.pop(0))
        stage = release_components.pop(0)
    except IndexError:
        pass
    return major_release, minor_release, stage


def set_spec_version(spec_file, version, release):
    version_regex = re.compile("^(version:\s*)(.+)$", re.IGNORECASE)
    release_regex = re.compile("^(release:\s*)(.+)$", re.IGNORECASE)
    in_f = open(spec_file, 'r')
    out_f = open(spec_file + ".new", 'w')
    for line in in_f.readlines():
        match = re.match(version_regex, line)
        if match:
            line = "".join((match.group(1), version, "\n"))
        match = re.match(release_regex, line)
        if match:
            line = "".join((match.group(1), release, "%{?dist}\n"))

        out_f.write(line)

    in_f.close()
    out_f.close()
    shutil.move(spec_file + ".new", spec_file)
    print "updated %s to %s-%s" % (spec_file, version, release)


def replace_version(line, new_version):
    """
    COPIED FROM TITO

    Attempts to replace common setup.py version formats in the given line,
    and return the modified line. If no version is present the line is
    returned as is.

    Looking for things like version="x.y.z" with configurable case,
    whitespace, and optional use of single/double quotes.
    """
    # Mmmmm pretty regex!
    ver_regex = re.compile("(\s*)(version)(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)",
            re.IGNORECASE)
    m = ver_regex.match(line)
    if m:
        result_tuple = list(m.group(1, 2, 3, 4, 5, 6))
        result_tuple.append(new_version)
        result_tuple.extend(list(m.group(8, 9)))
        new_line = "%s%s%s%s%s%s%s%s%s\n" % tuple(result_tuple)
        return new_line
    else:
        return line


def set_setup_py_version(root_directory, new_version):
    for setup_file in builder.find_all_setup_py_files(root_directory):
        print "updated %s: to %s" % (setup_file, new_version)
        f = open(setup_file, 'r')
        buf = StringIO()
        for line in f.readlines():
            buf.write(replace_version(line, new_version))
        f.close()

        # Write out the new setup.py file contents:
        f = open(setup_file, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()

    # We also have to check the __init__.py files since that is the more pythonic place to put it
    for init_py in builder.find_files_matching_pattern(root_directory, '__init__.py'):
        f = open(init_py, 'r')
        buf = StringIO()
        for line in f.readlines():
            buf.write(replace_version(line, new_version))
        f.close()

        # Write out the new setup.py file contents:
        f = open(init_py, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()


parser = argparse.ArgumentParser()
parser.add_argument("directory", help="The directory to search for spec files")
group = parser.add_mutually_exclusive_group(required=True)
help_text = "Specify which part of the version is being updated. "\
            "Whichever part is specified will udpate all the other parts in accordance"\
            " with the version guildelines in the documentation. The version is "\
            "structured as major.minor.patch-release.stage (2.6.3-0.1.alpha)."\
            "If any part is updated the parts below it will be reset. "\
            "stage update 2.6.0-1 -> 2.6.1-0.1.alpha "\
            "stage update 2.6.1-0.3.alpha -> 2.6.1-0.4.beta"\
            "stage update 2.6.1-0.5.rc -> 2.6.1-1"\
            "patch update 2.6.1-1 -> 2.6.2-0.1.alpha"
group.add_argument("--update-type", choices=['major', 'minor', 'patch', 'release', 'stage'],
                   help=help_text)
group.add_argument("--version", help="Manually set full version (eg. 2.6.2-0.1.alpha)")

opts = parser.parse_args()

# Find the spec
spec_files = glob.glob(os.path.join(opts.directory, '*.spec'))
if not spec_files:
    print "Error, unable to find spec file in %s " % opts.directory
    sys.exit(1)

spec_file = spec_files[0]

# Get the components of the current version
if opts.update_type:
    full_version = builder.get_version_from_spec(spec_file)
    full_release = builder.get_release_from_spec(spec_file)
else:
    # user specified version so get it from there
    full_version, full_release = opts.version.split('-')

# print full_version
# print full_release


major_version, minor_version, patch_version = parse_version(full_version)
major_release, minor_release, stage = parse_release(full_release)

update_type = None
if opts.update_type:
    update_type = opts.update_type

# print [major_release, major_release, stage]

if update_type == 'major':
    major_version += 1
    minor_version = 0
    patch_version = 0
    major_release = 0
    minor_release = 1
    stage = 'alpha'
elif update_type == 'minor':
    minor_version += 1
    patch_version = 0
    major_release = 0
    minor_release = 1
    stage = 'alpha'
elif update_type == 'patch':
    patch_version += 1
    major_release = 0
    minor_release = 1
    stage = 'alpha'
elif update_type == 'release':
    if minor_release is None:
        major_release += 1
        minor_release = 1
        stage = 'alpha'
    else:
        minor_release += 1
elif update_type == 'stage':
    if stage is None:
        patch_version += 1
        major_release += 1
        minor_release = 1
        stage = 'alpha'
    elif stage == 'alpha':
        stage = 'beta'
        minor_release += 1
    elif stage == 'beta':
        stage = 'rc'
        minor_release += 1
    elif stage == 'rc':
        stage = None
        minor_release = None

calculated_version = "%s.%s.%s" % (major_version, minor_version, patch_version)

calculated_release = "%s" % major_release
# print [major_release, minor_release, stage]
if minor_release is not None:
    calculated_release += '.%s' % minor_release
if stage is not None:
    calculated_release += '.%s' % stage

python_version = calculated_version
if stage == 'alpha':
    python_version += 'a'
elif stage == 'beta':
    python_version += 'b'
elif stage == 'rc':
    python_version += 'c'
if minor_release is not None:
    python_version += '%s' % minor_release

# print "%s-%s" % (calculated_version, calculated_release)

# print python_version


# Update the spec file
set_spec_version(spec_file, calculated_version, calculated_release)
# find all the setup.py files and update them as well
set_setup_py_version(os.path.dirname(spec_file), python_version)
