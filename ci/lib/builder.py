#!/usr/bin/env python2
import fnmatch
import glob
import json
import os
import rpm
import sys
import shutil
import subprocess
import time
import uuid

import requests
import yaml

try:
    import koji
except ImportError:
    print("koji package is unavailable, attempts to build in koji will fail.")
    koji = None

home_directory = os.path.expanduser('~')
mysession = None


def init_koji():
    global mysession
    opts = {
        'cert': os.path.join(home_directory, '.katello.cert'),
        'ca': os.path.join(home_directory, '.katello-ca.cert'),
        'serverca': os.path.join(home_directory, '.katello-ca.cert')
    }

    mysession = koji.ClientSession("http://koji.katello.org/kojihub", opts)
    mysession.ssl_login(opts['cert'], opts['ca'], opts['serverca'])
    return mysession

ARCH = 'arch'
REPO_NAME = 'repo_name'
DIST_KOJI_NAME = 'koji_name'
PULP_PACKAGES = 'pulp_packages'
REPO_CHECKSUM_TYPE = 'checksum'
REPO_ALIAS = 'repo_alias'

# Using 'sha' instead of 'sha1' for EL5 because createrepo documentation
# indicates that 'sha1' may not be compatible with older versions of yum.

DISTRIBUTION_INFO = {
    'el5': {
        ARCH: ['i386', 'x86_64'],
        REPO_NAME: '5Server',
        REPO_ALIAS: ['5'],
        DIST_KOJI_NAME: 'rhel5',
        REPO_CHECKSUM_TYPE: 'sha'
    },
    'el6': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: '6Server',
        REPO_ALIAS: ['6'],
        DIST_KOJI_NAME: 'rhel6',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'el7': {
        ARCH: ['x86_64'],
        REPO_NAME: '7Server',
        REPO_ALIAS: ['7'],
        DIST_KOJI_NAME: 'rhel7',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc20': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-20',
        DIST_KOJI_NAME: 'fedora20',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc21': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-21',
        DIST_KOJI_NAME: 'fedora21',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc22': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-22',
        DIST_KOJI_NAME: 'fedora22',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc23': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-23',
        DIST_KOJI_NAME: 'fedora23',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc24': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-24',
        DIST_KOJI_NAME: 'fedora24',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc25': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-25',
        DIST_KOJI_NAME: 'fedora25',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
    'fc26': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-26',
        DIST_KOJI_NAME: 'fedora26',
        REPO_CHECKSUM_TYPE: 'sha256'
    },
}

SUPPORTED_DISTRIBUTIONS = ['el7', 'fc24', 'fc25', 'fc26']

DIST_LIST = DISTRIBUTION_INFO.keys()
WORKSPACE = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
WORKING_DIR = os.path.join(WORKSPACE, 'working')
MASH_DIR = os.path.join(WORKSPACE, 'mash')
TITO_DIR = os.path.join(WORKSPACE, 'tito')
CI_DIR = os.path.join(WORKSPACE, 'pulp-ci', 'ci')


def clone_branch(component):
    """
    Clone a git repository component into the working dir.

    Assumes the working dir has already been created and cleaned, if needed, before cloning.

    Returns the directory into which the branch was cloned.
    """
    print("Cloning from github: %s" % component['git_url'])
    # --branch will let you check out tags as a detached head
    command = ['git', 'clone', component['git_url'], '--branch',
               component['git_branch'], component['name']]
    subprocess.call(command, cwd=WORKING_DIR)
    return os.path.join(WORKING_DIR, component['name'])


def get_nvr_from_spec_file_in_directory(directory_path):
    """
    Find the first spec file in a directory and return the pacakge NVR from it

    :param directory_path:
    :type directory_path:
    :return:
    :rtype:
    """
    spec_files = glob.glob(os.path.join(directory_path, '*.spec'))
    if not spec_files:
        print("Error, unable to find spec file in %s " % directory_path)
        sys.exit(1)

    spec_file = spec_files[0]
    return get_package_nvr_from_spec(spec_file)


def find_all_spec_files(root_directory):
    """
    Find all spec files within a given root directory

    :param root_directory: The directory to search
    :type root_directory: str
    :return: list of canonical paths to spec files
    :rtype: list of str
    """
    print("Finding all spec files in %s" % root_directory)
    return find_files_matching_pattern(root_directory, '*.spec')


def find_files_matching_pattern(root_directory, pattern):
    """
    Find all spec files within a given root directory

    :param root_directory: The directory to search
    :type root_directory: str
    :param pattern: The regex to match files in a directory
    :type pattern: str`
    :return: list of canonical paths to spec files
    :rtype: list of str
    """
    root_len = len(root_directory)
    for root, dirnames, filenames in os.walk(root_directory):
        # don't look for things in playpen or testing directories
        if root.find('playpen', root_len) != -1 or \
                        root.find('test', root_len) != -1 or \
                        root.find('deps', root_len) != -1 or \
                        root.find('build', root_len) != -1:
            continue
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)


def find_all_setup_py_files(root_directory):
    """
    Find all setup.py files within a given root directory structure

    :param root_directory: The directory to search
    :type root_directory: str
    :return: list of canonical paths to spec files
    :rtype: list of str
    """
    return find_files_matching_pattern(root_directory, 'setup.py')


def get_version_from_spec(spec_file):
    """
    Return the version from the spec
    :param spec_file: The path to a spec file
    :type spec_file: str
    :return: Version field
    :rtype: str
    """
    # Get the dep name & version
    spec = rpm.spec(spec_file)
    return spec.sourceHeader[rpm.RPMTAG_VERSION]


def get_release_from_spec(spec_file):
    """
    Return the release from a spec file
    :param spec_file: The path to a spec file
    :type spec_file: str
    :return: Release field without the dist macro
    :rtype: str
    """
    # Get the dep name & version
    spec = rpm.spec(spec_file)
    release = spec.sourceHeader[rpm.RPMTAG_RELEASE]
    # split the dist from the end of the nvr
    release = release[:release.rfind('.')]
    return release


def get_package_name_from_rpm(rpm_file):
    """
    Return the name of the package from an srpm file

    :param rpm_file: The path to a spec file
    :type rpm_file: str
    :return: the name of the package
    :rtype: str
    """
    ts = rpm.TransactionSet()
    with open(rpm_file, 'r') as fd:
        h = ts.hdrFromFdno(fd)
        package_name = h[rpm.RPMTAG_NAME]
    return package_name


def get_package_nvr_from_spec(spec_file):
    """
    Return a list of the NVR required for a given spec file
    :param spec_file: The path to a spec file
    :type spec_file: str
    :return: list of nevra that should be built for that spec file
    :rtype: str
    """
    # Get the dep name & version
    spec = rpm.spec(spec_file)
    package_nvr = spec.sourceHeader[rpm.RPMTAG_NVR]
    # split the dist from the end of the nvr
    package_nvr = package_nvr[:package_nvr.rfind('.')]
    return package_nvr


def get_package_nevra(package_nvr, dists):
    """
    Yield the fully qualified build names in koji for a given
    package nvr and the dists for which the package should be built

    :param package_nvr: package NVR from the RPM header stripped of the dist
    :type package_nvr: str
    :param dists: list distribution names for which this package should be built
    :type dists: list of str
    """
    for dist in dists:
        dep_nevra = "%s.%s" % (package_nvr, dist)
        yield dep_nevra


def get_dist_from_koji_build_name(koji_build_name):
    """
    Split the dist from the end of the koji build name
    :param koji_build_name: The full build name including the dist
    :type koji_build_name: str
    :return: The short name of the dist from the build
    :rtype: str
    """
    return koji_build_name[koji_build_name.rfind('.')+1:]


def get_built_dependencies(dependency_dir, dists=None):
    """
    Generator to yield the nevra of all deps that should be prebuilt in koji.
    The string yielded by this generator can be used to lookup a particular koji build

    :param dependency_dir: The directory from which the dependencies should be read
    :type dependency_dir: str
    """
    # Find all spec files:
    for spec_file in find_all_spec_files(dependency_dir):
        package_nvr = get_package_nvr_from_spec(spec_file)
        dists_from_dep = get_dists_for_spec(spec_file)
        get_package_nevra(package_nvr, dists_from_dep)

    # Process the external deps listing
    deps_file = os.path.join(dependency_dir, 'external_deps.json')
    if os.path.exists(deps_file):
        get_build_names_from_external_deps_file(deps_file)


def get_dists_for_spec(spec_file, include_unsupported=False):
    """
    read the dist_list.txt file to get the distributions for which the spec file should be built

    :param spec_file: The spec file that should be targeted
    :type spec_file: str
    :return: list of distributions for which this spec file should be built
    :rtype: list of str
    """
    dep_directory = os.path.dirname(spec_file)
    dists_from_dep = []
    # Get the list of distributions we need it for
    dist_list_file = os.path.join(dep_directory, 'dist_list.txt')
    try:
        with open(dist_list_file, 'r') as handle:
            line = handle.readline()
            line = line.strip()
            dists_from_dep = line.split(' ')
    except IOError:
        print("dist_list.txt file not found for %s." % dep_directory)
    if not include_unsupported:
        dists_from_dep = list(filter(lambda dist: dist in SUPPORTED_DISTRIBUTIONS, dists_from_dep))
    return dists_from_dep


def get_urls_for_build(koji_session, build_name, rpmsig=None):
    """
    Generator to build all the urls & relative download directories for
    a given builder

    Yields (str, str) (url on koji server, local relative path)

    :param koji_session: the session object used to talk to Koji
    :type koji_session: koji.ClientSession
    :param dependency_dir: The directory to search for dependencies
    :type dependency_dir: str
    """
    info = koji_session.getBuild(build_name)
    rpms = koji_session.listRPMs(buildID=info['id'], arches=None)
    koji_url = "http://koji.katello.org"
    for rpm_listing in rpms:
        # Build the rpm URL on koji
        package_info = {
            'name': info['package_name'],
            'version': rpm_listing['version'],
            'release': rpm_listing['release']
        }
        koji_dir = "/packages/%(name)s/%(version)s/%(release)s/" % package_info
        # We don't honor rpmsig for el5 since the signature can't be parsed by el5 systems
        if rpmsig and rpm_listing['release'].find('.el5') == -1:
            koji_dir = koji_dir + "data/signed/%s/" % rpmsig

        fname = koji.pathinfo.rpm(rpm_listing)
        location_on_koji = "%s%s%s" % (koji_url, koji_dir, fname )
        # print(location_on_koji)
        # calculate the relative directory for the download
        rpm_nvr = rpm_listing['nvr']
        rpm_dist = rpm_nvr[rpm_nvr.rfind('.')+1:]

        repo_name = DISTRIBUTION_INFO[rpm_dist][REPO_NAME]
        target_download_directory = os.path.join(repo_name, fname)
        yield location_on_koji, target_download_directory


def get_deps_urls(koji_session, dependency_dir, rpmsig=None):
    """
    Generator to build all the urls & relative download directories for all
    the dependencies of a given deps directory

    Yields (str, str) (url on koji server, local relative path)

    :param koji_session: the session object used to talk to Koji
    :type koji_session: koji.ClientSession
    :param dependency_dir: The directory to search for dependencies
    :type dependency_dir: str
    """
    for build in get_built_dependencies(dependency_dir):
        info = koji_session.getBuild(build)
        rpms = koji_session.listRPMs(buildID=info['id'], arches=None)
        koji_url = "http://koji.katello.org"
        for rpm_listing in rpms:
            # Build the rpm URL on koji
            package_info = {
                'name': info['package_name'],
                'version': rpm_listing['version'],
                'release': rpm_listing['release']
            }
            koji_dir = "/packages/%(name)s/%(version)s/%(release)s/" % package_info
            if rpmsig:
                koji_dir = koji_dir + "data/signed/%s/" % rpmsig


def download_builds(target_dir, url_generator):
    """

    :param target_dir: The target directory where all the builds should
                       should be assembled
    :type target_dir: str
    :param url_generator: generator created by the  get_urls_for_build method
    :type url_generator: get_urls_for_build generator
    """
    for url_to_download, target in url_generator:
        print("Downloading %s from %s" % (target, url_to_download))
        local_file_name = os.path.join(target_dir, os.path.basename(target))

        base_dir = os.path.dirname(local_file_name)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        r = requests.get(url_to_download, stream=True)
        r.raise_for_status()
        with open(local_file_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()


def normalize_directories(target_dir):
    """
    Loop through all the loose rpms in the target directory and move them into
    the correct repository locations

    :param target_dir: Directory containing all the rpm & src_rpm files
    :type target_dir: str
    """
    for file_name in glob.glob(os.path.join(target_dir, '*.rpm')):
        file_parts = file_name.split('.')
        file_dist = file_parts[-3]
        file_arch = file_parts[-2]
        repo_name = DISTRIBUTION_INFO[file_dist][REPO_NAME]
        base_dir = os.path.join(target_dir, repo_name)
        target_dirs = []
        if file_arch == 'noarch':
            target_dirs = [os.path.join(base_dir, arch)
                           for arch in DISTRIBUTION_INFO[file_dist][ARCH]]
        else:
            target_dirs.append(os.path.join(base_dir, file_arch))

        for arch_dir in target_dirs:
            # Rename the i686 to i386 since rhel & fedora both identify as i386
            arch_dir = arch_dir.replace('i686', 'i386')
            ensure_dir(arch_dir, clean=False)
            shutil.copy(os.path.join(target_dir, file_name), arch_dir)

        os.unlink(file_name)


def build_repositories(target_dir, comps_file=None):
    for distkey in DIST_LIST:
        distvalue = DISTRIBUTION_INFO[distkey]
        repo_dir = distvalue[REPO_NAME]
        checksum_type = distvalue[REPO_CHECKSUM_TYPE]
        for arch_name in ['i386', 'x86_64', 'src']:
            arch_dir = os.path.join(target_dir, repo_dir, arch_name)
            if not os.path.exists(arch_dir):
                continue
            # create the repo
            if comps_file and arch_name is not 'src':
                command = "createrepo -s %s -g %s %s" % (checksum_type, comps_file, arch_dir)
            else:
                command = "createrepo -s %s  %s" % (checksum_type, arch_dir)
            subprocess.check_call(command, shell=True)

        # create other symlinks
        if REPO_ALIAS in distvalue:
            dist_repo_dir = os.path.join(target_dir, repo_dir)
            if os.path.exists(dist_repo_dir):
                # only create aliases if the alias source exists
                for alias_value in distvalue[REPO_ALIAS]:
                    command = 'ln -rs %s %s' % (dist_repo_dir,
                                                os.path.join(target_dir, alias_value))
                    subprocess.check_call(command, shell=True)


def ensure_dir(target_dir, clean=True):
    """
    Ensure that the directory specified exists and is empty.  By default this will delete
    the directory if it already exists

    :param target_dir: The directory to process
    :type target_dir: str
    :param clean: Whether or not the directory should be removed and recreated
    :type clean: bool
    """
    if clean:
        shutil.rmtree(target_dir, ignore_errors=True)
    try:
        os.makedirs(target_dir)
    except OSError:
        pass


def build_srpm_from_spec(spec_dir, output_dir, testing=True, tag=None, dist=None):
    """
    Build the srpms required for a given spec directory and distribution list

    The SRPM files are saved in the <output_dir>/<distribution_name>/srpm.rpm file

    :param spec_dir: The directory where the spec file is located
    :type spec_dir: str
    :param output_dir: the output directory where the results should be saved
    :type output_dir: str
    :param testing: Whether or not this is a testing build
    :type testing: bool
    :param tag: The specific package tag to build (instead of the latest
    :type tag: str
    :parm dist: The specific distribution to build for.  If not specified
                the values are read from the dist_list.txt associated with the spec
    :type dist: str
    """
    spec_glob = os.path.join(spec_dir, '*.spec')
    if not isinstance(dist, list):
        distributions = [dist]
    elif dists:
        distributions = dist
    else:
        distributions = get_dists_for_spec(glob.glob(spec_glob)[0])

    for dist in distributions:
        tito_path = os.path.join(output_dir, dist)
        ensure_dir(tito_path, clean=False)
        distribution = ".%s" % dist
        print("Building %s Srpm for %s" % (spec_dir, distribution))
        command = ['tito', 'build', '--offline', '--srpm', '--output', tito_path,
                   '--dist', distribution]
        if testing:
            command.append('--test')

        if tag:
            command.append('--tag')
            command.append(tag)

        subprocess.check_call(command, cwd=spec_dir)


def build_with_koji(build_tag_prefix, srpm_dir, scratch=False):
    """
    Run builds of all the pulp srpms on koji

    :param build_tag_prefix: The prefix for the build tag to build using koji.  For example
           pulp-2.4-testing
    :type build_tag_prefix: str
    :param srpm_dir: The srpm directory, it is assumed that this is structured as
                     srpm_dir/<dist>/<srpm_files>
    :type srpm_dir: str
    :param scratch: Whether or not to run a scratch build with koji
    :type scratch: bool
    :returns: list of task_ids to monitor
    :rtype: list of str
    """
    builds = []
    upload_prefix = 'pulp-build/%s' % str(uuid.uuid4())
    dist_list = os.listdir(srpm_dir)

    for dist in dist_list:
        dist_srpm_dir = os.path.join(srpm_dir, dist)
        build_target = "%s-%s" % (build_tag_prefix,
                                  (DISTRIBUTION_INFO.get(dist)).get(DIST_KOJI_NAME))
        # Get all the source RPMs that were built
        # submit each srpm
        for dir_file in os.listdir(dist_srpm_dir):
            if dir_file.endswith(".rpm"):
                full_path = os.path.join(dist_srpm_dir, dir_file)
                # make sure the package exists in the tag before building
                # Get the package name from the srpm
                package_name = get_package_name_from_rpm(full_path)
                # Always add the package as the jenkins user if required
                if not mysession.checkTagPackage(build_target, package_name):
                    mysession.packageListAdd(build_target, package_name, 'jenkins')

                # upload the file
                print("Uploading %s" % dir_file)
                mysession.uploadWrapper(full_path, upload_prefix)
                # Start the koji build
                source = "%s/%s" % (upload_prefix, dir_file)
                task_id = int(mysession.build(source, build_target, {'scratch': scratch}))
                print("Created Build Task: %i" % task_id)
                builds.append(task_id)
    return builds


def wait_for_completion(build_ids):
    """
    For a given list of build ids.  Monitor them and wait for all to complete
    """
    for task_id in build_ids:
        while True:
            info = mysession.getTaskInfo(task_id)
            state = koji.TASK_STATES[info['state']]
            if state in ['FAILED', 'CANCELED']:
                msg = "Task %s: %i" % (state, task_id)
                raise Exception(msg)
            elif state in ['CLOSED']:
                print("Task %s: %i" % (state, task_id))
                break
            time.sleep(5)


def download_rpms_from_tag(tag, output_directory, rpmsig=None):
    """
    For a given tag download all the latest contents of that tag to the given output directory.
    This will create subdirectories for each arch in the tag (noarch, i686, x86_64,
    src) assuming that the contains packages with that tag.

    :param tag: The koji tag to get the files from
    :type tag: str
    :param output_directory: The directory to save the output into
    :type output_directory: str
    """
    # clean out and ensure the output directory exists
    shutil.rmtree(output_directory, ignore_errors=True)
    os.makedirs(output_directory)

    # arches I care about = src, noarch, i686 and x86_64
    rpms = mysession.getLatestRPMS(tag)

    # Iterate through the packages and pull their output from koji with wget
    os.chdir(output_directory)
    for package in rpms[1]:
        koji_dir = "/packages/%(name)s/%(version)s/%(release)s/" % package
        # append the signature to download URL if needed
        if rpmsig:
            koji_dir = koji_dir + "data/signed/%s/" % rpmsig
        data_dir = "/packages/%(name)s/%(version)s/%(release)s/data" % package
        koji_url = "http://koji.katello.org"
        location_on_koji = "%s%s" % (koji_url, koji_dir)
        # the wget commands are slightly different depending on if we are
        # downloading signed RPMs or not.
        if rpmsig:
            command = "wget -r -np -nH --cut-dirs=7 -R index.htm*  %s" % \
                      (location_on_koji)
        else:
            command = "wget -r -np -nH --cut-dirs=4 -R index.htm*  %s -X %s" % \
                      (location_on_koji, data_dir)
        subprocess.check_call(command, shell=True)


def download_rpms_from_task_to_dir(task_id, output_directory):
    """
    Download all of the rpm files from a given koji task into a specified directory

    :param task_id: The task id to query
    :type task_id: str
    :param output_directory: The directory to save the files in
    :type output_directory: str
    """
    ensure_dir(output_directory, clean=False)
    output_list = mysession.listTaskOutput(int(task_id))
    for file_name in output_list:
        if file_name.endswith('.rpm'):
            print('Downloading %s to %s' % (file_name, output_directory))
            result = mysession.downloadTaskOutput(int(task_id), file_name)
            target_location = os.path.join(output_directory, file_name)
            with open(target_location, 'w+') as file_writer:
                file_writer.write(result)


def download_rpms_from_scratch_tasks(output_directory, task_list):
    """
    Download all RPMS from the scratch tasks for a given distribution

    :param output_directory: The root directory for the distribution files to be saved in
    :type output_directory: str
    :param dist: The distribution to get the tasks from
    :type dist: str
    :param task_list: list of tasks to download rpms from
    :type task_list: list of koji tasks
    """
    ensure_dir(output_directory, clean=False)
    for parent_task_id in task_list:
        descendants = mysession.getTaskDescendents(int(parent_task_id))
        for task_id in descendants:
            print('Downloading %s to %s' % (task_id, output_directory))
            download_rpms_from_task_to_dir(task_id, output_directory)


def get_tag_packages(tag):
    """
    Get the set of packages currently associated with a tag

    :param tag: the tag to search for in koji
    :type tag: str

    :returns: a set of package names
    :rtype: set of str
    """
    dsttag = mysession.getTag(tag)
    pkglist = set([(p['package_name']) for p in mysession.listPackages(tagID=dsttag['id'])])
    return pkglist


def get_supported_dists_for_dep(dep_directory):
    """
    Get a list of the supported distributions for the dependency in the given directory

    :param dep_directory: The full path of the directory where the dependency is stored
    :type dep_directory: str

    :returns: a set of dist keys for the dists that this dep supports
    :rtype: set of str
    """
    dist_list_file = os.path.join(dep_directory, 'dist_list.txt')
    try:
        with open(dist_list_file, 'r') as handle:
            line = handle.readline()
            line = line.strip()
            dists_from_dep = line.split(' ')
    except IOError:
        print("dist_list.txt file not found for %s." % dep_directory)
        sys.exit(1)

    return set(dists_from_dep)


def get_build_names_from_external_deps_file(external_deps, include_unsupported=False):
    """
    Get the dictionary of all the external package deps. Befault, the returned deps
    filter out unsupported dists.

    :return: Full path/filename of the external deps file
    :rtype: str
    """
    client_deps = ['gofer', 'python-isodate', 'python-amqp', 'python-qpid']

    with open(external_deps) as file_handle:
            deps_list = json.load(file_handle)
            for dep_info in deps_list:
                for dist in dep_info[u'platform']:
                    if not include_unsupported and \
                           dist not in SUPPORTED_DISTRIBUTIONS and \
                           dep_info['name'] not in client_deps:
                        continue
                    package_nevra = "%s-%s.%s" % (dep_info['name'], dep_info[u'version'], dist)
                    yield package_nevra


def does_git_tag_exist(tag, directory):
    """
    Check if the specified tag exists in the git repo in the specified directory

    :param tag: The tag to search for in the git repository
    :type tag: str
    :param directory: The directory containing a git repo
    :type directory: str

    :return: Whether or not the specified tag exists in the repository
    :rtype: bool
    """
    command = "git tag -l {tag}".format(tag=tag)
    output = subprocess.check_output(command, shell=True, cwd=directory)
    if output:
        return True
    return False


def load_config(config_name):
    # Get the config
    config_file = os.path.join(os.path.dirname(__file__), '..',
                               'config', 'releases', '%s.yaml' % config_name)
    if not os.path.exists(config_file):
        print("Error: %s not found. " % config_file)
        sys.exit(1)
    with open(config_file, 'r') as config_handle:
        config = yaml.safe_load(config_handle)
    return config


def components(configuration):
    return configuration['repositories']
