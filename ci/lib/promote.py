import re
import subprocess
import sys


def get_promotion_chain(git_directory, git_branch, upstream_name='origin', parent_branch=None):
    """
    For a given git repository & branch, determine the promotion chain

    Following the promotion path defined for pulp figure out what the full promotion
    path to master is from wherever we are.

    For example if given 2.5-release for pulp the promotion path
    would be 2.5-release -> 2.5-testing -> 2.5-dev -> 2.6-dev -> master

    If parent_branch is not None, the branch will be prepended to the promotion chain of the value
    of parent_branch.

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :param git_branch: The git branch to start with
    :type git_branch: str
    :param upstream_name: The name of the upstream repo, defaults to 'origin', will be
                          overridden by the upstream name if specified in the branch
    :param upstream_name: str
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
    branch_regex = "(\d+.\d+)-(dev|testing|release)"
    match = re.search(branch_regex, git_branch)
    source_branch_version = match.group(1)
    source_branch_stream = match.group(2)

    # get the branch list
    raw_branch_list = subprocess.check_output(['git', 'branch', '-r'], cwd=git_directory)

    lines = raw_branch_list.splitlines()

    target_branch_versions = set()
    all_branches = set()

    for line in lines:
        line = line.strip()
        # print line
        match = re.search(branch_regex, line)
        if match:
            all_branches.add(match.group(0))
            branch_version = match.group(1)
            if branch_version > source_branch_version:
                target_branch_versions.add(branch_version)
    result_list = [git_branch]
    if source_branch_stream == 'release':
        result_list.append("%s-testing" % source_branch_version)
        result_list.append("%s-dev" % source_branch_version)
    if source_branch_stream == 'testing':
        result_list.append("%s-dev" % source_branch_version)

    result_list.extend(["%s-dev" % branch_version
                        for branch_version in sorted(target_branch_versions)])

    # Do this check before adding master since we explicitly won't match master in the above regex
    if not set(result_list).issubset(all_branches):
        missing_branches = set(result_list).difference(all_branches)
        print "Error creating git branch promotion list.  The following branches are missing: "
        print missing_branches
        sys.exit(1)

    result_list.append('master')
    if parent_branch:
        result_list.insert(0, actual_branch)
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
        print "checking log comparision of %s -> %s" % (pair[0], pair[1])
        output = subprocess.check_output(['git', 'log', "^%s" % pair[1], pair[0]],
                                         cwd=git_directory)
        if output:
            print "ERROR: in %s: branch %s has not been merged into %s" % \
                  (git_directory, pair[0], pair[1])
            print "Run 'git log ^%s %s' to view the differences." % (pair[1], pair[0])
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
    return subprocess.check_output(command, cwd=git_directory).strip()


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
    return subprocess.check_output(command, cwd=git_directory).strip()


def get_local_git_branches(git_directory):
    command = "git for-each-ref --format %(refname:short) refs/heads/"
    command = command.split(' ')
    lines = subprocess.check_output(command, cwd=git_directory)
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

    if not local_branch in get_local_git_branches(git_directory):
        subprocess.check_call(['git', 'checkout', '-b', local_branch, full_name],
                              cwd=git_directory)

    subprocess.check_call(['git', 'checkout', local_branch], cwd=git_directory)

    # validate that the upstream branch is what we expect it to be
    upstream_branch = get_current_git_upstream_branch(git_directory)
    if upstream_branch != full_name:
        print "Error checking out %s in %s" % (full_name, git_directory)
        print "The upstream branch was already set to %s" % upstream_branch
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
        print "Merging %s into %s" % (local_source_branch, target_branch)
        subprocess.check_call(['git', 'merge', '-s', 'ours', local_source_branch, '--no-edit'],
                              cwd=git_directory)
        if push:
            subprocess.call(['git', 'push'], cwd=git_directory)

    # Set the branch back tot he one we started on
    checkout_branch(git_directory, starting_branch)
