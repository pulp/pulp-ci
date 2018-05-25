import glob
import re
import os
import shutil
import subprocess
import sys

try:
    # py2
    from StringIO import StringIO
except ImportError:
    # py3
    from io import StringIO

VERSION_REGEX = "(\s*)(version)(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)"
RELEASE_REGEX = "(\s*)(release)(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)"


def get_promotion_chain(git_directory, git_branch, upstream_name='origin', parent_branch=None):
    """
    For a given git repository & branch, determine the promotion chain

    Following the promotion path defined for pulp figure out what the full promotion
    path to master is from wherever we are.

    For example if given 2.5-release for pulp the promotion path
    would be 2.5-release -> 2.5-dev -> 2.6-dev -> master

    If parent_branch is not None, the branch will be prepended to the promotion chain of the value
    of parent_branch.

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :param git_branch: The git branch to start with
    :type git_branch: str
    :param upstream_name: The name of the upstream repo, defaults to 'origin', will be
                          overridden by the upstream name if specified in the branch
    :param upstream_name: str
    :param parent_branch: Name of branch that should be used to calculate the promotion chain. This
                          is used for building from hotfix branch.
    :type parent_branch: str
    :return: list of branches that the specified branch promotes to
    :rtype: list of str
    """
    if parent_branch:
        actual_branch = git_branch
        if actual_branch.find('/') != -1:
            actual_branch = actual_branch[actual_branch.find('/')+1:]
        git_branch = parent_branch
    if git_branch.find('/') != -1:
        upstream_name = git_branch[:git_branch.find('/')]
        git_branch = git_branch[git_branch.find('/')+1:]

    git_branch = git_branch.strip()

    # parse the branch into its component parts
    if git_branch == 'master':
        return ['master']

    # parse the git_branch: x.y-(dev|testing|release)
    branch_regex = "(\d+.\d+)-(dev|testing|release|dev-tmp)$"
    match = re.search(branch_regex, git_branch)
    source_branch_version = match.group(1)
    source_branch_stream = match.group(2)
    source_branch_major, source_branch_minor = map(int, source_branch_version.split('.'))

    # get the branch list
    raw_branch_list = subprocess.check_output('git branch -r|sort -V', cwd=git_directory,
                                              shell=True).decode('utf8')
    lines = raw_branch_list.splitlines()

    # the order of items in these matters, so we start with list()
    target_branch_versions = list()
    all_branches = list()

    for line in lines:
        line = line.strip()
        # print(line)
        match = re.search(branch_regex, line)
        if match:
            all_branches.append(match.group(0))
            branch_version = match.group(1)
            branch_major, branch_minor = map(int, branch_version.split('.'))
            # this check only includes changes from the same major version
            if (branch_major == source_branch_major and branch_minor > source_branch_minor and
                    branch_version not in target_branch_versions):
                target_branch_versions.append(branch_version)
    result_list = [git_branch]
    if source_branch_stream == 'release':
        result_list.append("%s-dev" % source_branch_version)

    result_list.extend(["%s-dev" % branch_version
                        for branch_version in target_branch_versions])

    # Do this check before adding master since we explicitly won't match master in the above regex
    if not set(result_list).issubset(set(all_branches)):
        missing_branches = set(result_list).difference(set(all_branches))
        print("Error creating git branch promotion list.  The following branches are missing: ")
        print(missing_branches)
        sys.exit(1)

    # For the moment, do not merge any branch named 3.0-dev to master
    if not result_list[-1] == '3.0-dev':
        result_list.append('master')

    if parent_branch:
        result_list.insert(0, actual_branch)

    print("Branch promotion chain:")
    print(" -> ".join(result_list))

    result_list = ["%s/%s" % (upstream_name, item) for item in result_list]
    return result_list


def generate_promotion_pairs(promotion_chain):
    """
    For all the items in a promotion path, yield the list of individual promotions that
    will need to be applied

    :param promotion_chain: list of branches that will need to be promoted
    :type promotion_chain: list of str
    """
    for i in range(0, len(promotion_chain), 1):
        if i < (len(promotion_chain) - 1):
            yield promotion_chain[i:i + 2]


def check_merge_forward(git_directory, promotion_chain):
    """
    For a given git repo & promotion path, validate that all branches have been merged forward

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :param promotion_chain: git branch promotion path
    :type promotion_chain: list of str
    """
    for pair in generate_promotion_pairs(promotion_chain):
        print("checking log comparision of %s -> %s" % (pair[0], pair[1]))
        output = subprocess.check_output(['git', 'log', "^%s" % pair[1], pair[0]],
                                         cwd=git_directory).decode('utf8')
        if output:
            print("ERROR: in %s: branch %s has not been merged into %s" %
                  (git_directory, pair[0], pair[1]))
            print("Run 'git log ^%s %s' to view the differences." % (pair[1], pair[0]))
            sys.exit(1)


def get_current_git_upstream_branch(git_directory):
    """
    For a given git directory, get the current remote branch

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :return: remote branch
    :rtype: str
    """
    command = 'git rev-parse --abbrev-ref --symbolic-full-name @{u}'
    command = command.split(' ')
    return subprocess.check_output(command, cwd=git_directory).decode('utf8').strip()


def get_current_git_branch(git_directory):
    """
    For a given git directory, get the current branch

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :return: remote branch
    :rtype: str
    """
    command = 'git rev-parse --abbrev-ref HEAD'
    command = command.split(' ')
    return subprocess.check_output(command, cwd=git_directory).decode('utf8').strip()


def get_local_git_branches(git_directory):
    command = "git for-each-ref --format %(refname:short) refs/heads/"
    command = command.split(' ')
    lines = subprocess.check_output(command, cwd=git_directory).decode('utf8')
    results = [item.strip() for item in lines.splitlines()]
    return set(results)


def checkout_branch(git_directory, branch_name, remote_name='origin'):
    """
    Ensure that branch_name is checkout from the given upstream

    :param git_directory: directory containing the git project
    :type git_directory:  str
    :param branch_name: The local branch name. if the remote is specified in the branch name
        eg upstream/2.6-dev then the remote specified in the branch_name will take
        precidence over the remote_name specified as a parameter
    :type branch_name: str
    :param remote_name: The name of the remote git repo to use, is ignored if the
        remote is specified as part of the branch name
    :type remote_name: str
    """
    if branch_name.find('/') != -1:
        local_branch = branch_name[branch_name.find('/')+1:]
        remote_name = branch_name[:branch_name.find('/')]
    else:
        local_branch = branch_name

    local_branch = local_branch.strip()

    full_name = '%s/%s' % (remote_name, local_branch)

    if local_branch not in get_local_git_branches(git_directory):
        subprocess.check_call(['git', 'checkout', '-b', local_branch, full_name],
                              cwd=git_directory)

    subprocess.check_call(['git', 'checkout', local_branch], cwd=git_directory)

    # validate that the upstream branch is what we expect it to be
    upstream_branch = get_current_git_upstream_branch(git_directory)
    if upstream_branch != full_name:
        print("Error checking out %s in %s" % (full_name, git_directory))
        print("The upstream branch was already set to %s" % upstream_branch)
        sys.exit(1)

    subprocess.check_call(['git', 'pull'], cwd=git_directory)


def merge_forward(git_directory, push=False, parent_branch=None):
    """
    From whatever the current checkout is, merge it forward

    :param git_directory: directory containing the git project
    :type git_directory:  str
    :param push: Whether or not we should push the results to github
    :type push: bool
    """
    starting_branch = get_current_git_branch(git_directory)
    branch = get_current_git_upstream_branch(git_directory)
    chain = get_promotion_chain(git_directory, branch, parent_branch=parent_branch)

    for source_branch, target_branch in generate_promotion_pairs(chain):
        checkout_branch(git_directory, source_branch)
        checkout_branch(git_directory, target_branch)
        local_source_branch = source_branch[source_branch.find('/')+1:]
        print("Merging %s into %s" % (local_source_branch, target_branch))
        subprocess.check_call(['git', 'merge', '-s', 'ours', local_source_branch, '--no-edit'],
                              cwd=git_directory)
        if push:
            subprocess.call(['git', 'push', '-v'], cwd=git_directory)

    # Set the branch back tot he one we started on
    checkout_branch(git_directory, starting_branch)


def split_version(evr):
    """
    split epoch:version-release into (epoch:version, release)
    """
    return evr.rsplit('-', 1)


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
    old_release_regex = re.compile("^(release:\s*)(.+)$", re.IGNORECASE)
    new_release_regex = re.compile("^(%global release_number\s*)(.+)$", re.IGNORECASE)

    in_f = open(spec_file, 'r')
    out_f = open(spec_file + ".new", 'w')
    for line in in_f.readlines():
        match = re.match(version_regex, line)
        if match:
            line = "".join((match.group(1), version, "\n"))
        match = re.match(new_release_regex, line)
        if match:
            line = "".join((match.group(1), release, "\n"))
        match = re.match(old_release_regex, line)
        if match and 'release_number' not in line:
            line = "".join((match.group(1), release, "%{?dist}\n"))
        out_f.write(line)

    in_f.close()
    out_f.close()
    shutil.move(spec_file + ".new", spec_file)
    print("updated %s to %s-%s" % (spec_file, version, release))


def replace_version(line, new_version, regex):
    """
    COPIED FROM TITO

    Attempts to replace common setup.py version formats in the given line,
    and return the modified line. If no version is present the line is
    returned as is.

    Looking for things like version="x.y.z" with configurable case,
    whitespace, and optional use of single/double quotes.
    """
    # Mmmmm pretty regex!
    ver_regex = re.compile(regex, re.IGNORECASE)
    m = ver_regex.match(line)
    if m:
        result_tuple = list(m.group(1, 2, 3, 4, 5, 6))
        result_tuple.append(new_version)
        result_tuple.extend(list(m.group(8, 9)))
        new_line = "%s%s%s%s%s%s%s%s%s\n" % tuple(result_tuple)
        return new_line
    else:
        return line


def find_replace_in_files(root_directory, file_mask, new_version, version_regex):
    from .builder import find_files_matching_pattern
    # We also have to check the __init__.py files since that is the more pythonic place to put it
    for file_name in find_files_matching_pattern(root_directory, file_mask):
        f = open(file_name, 'r')
        buf = StringIO()
        for line in f.readlines():
            new_line = replace_version(line, new_version, version_regex)
            if new_line != line:
                print("updated %s: to %s" % (file_name, new_version))
            buf.write(new_line)
        f.close()

        # Write out the new setup.py file contents:
        f = open(file_name, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()


def calculate_version(full_version, full_release, update_type):
    """
    Given a version, release, and update type, increment the version/release based on that type
    """
    major_version, minor_version, patch_version = parse_version(full_version)
    major_release, minor_release, stage = parse_release(full_release)

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
            major_release += 1

    calculated_version = "%s.%s.%s" % (major_version, minor_version, patch_version)

    calculated_release = "%s" % major_release
    if minor_release is not None:
        calculated_release += '.%s' % minor_release
    if stage is not None:
        calculated_release += '.%s' % stage

    return calculated_version, calculated_release


def to_python_version(version, release=None):
    """
    convert an rpm-style version and release into a python version string

    can split a complete rpm version-release string, if release is not passed
    """
    if release is None:
        version, release = split_version(version)
    major_version, minor_version, patch_version = parse_version(version)
    major_release, minor_release, stage = parse_release(release)

    if patch_version > 0:
        # Can use the x.y.z component directory if not patch version 0
        python_version = version
    else:
        python_version = "%d.%d" % (major_version, minor_version)
    if stage in ('alpha', 'beta', 'rc'):
        if stage == 'alpha':
            python_version += 'a'
        elif stage == 'beta':
            python_version += 'b'
        elif stage == 'rc':
            python_version += 'c'
        python_version += '%s' % minor_release

    return python_version


def update_versions(project_dir, version, release):
    """
    Update the versions contained in files located in the same dir (or subdirs) of a spec file.

    In addition to the spec file itself, this includes python setup.py files, __init__.py, and
    the sphinx conf.py
    """
    # Update the all the files
    python_version = to_python_version(version, release)
    find_replace_in_files(project_dir, 'setup.py', python_version, VERSION_REGEX)
    find_replace_in_files(project_dir, '__init__.py', python_version, VERSION_REGEX)
    find_replace_in_files(project_dir, 'conf.py', python_version, VERSION_REGEX)
    find_replace_in_files(project_dir, 'conf.py', python_version, RELEASE_REGEX)
