#!/usr/bin/env python

import argparse
import subprocess
import os
import re
from shutil import copyfile

from lib import builder, promote
from lib.builder import WORKING_DIR


LATEST = '2.13'

USERNAME = '57600fb10c1e664383000229'
HOSTNAME = 'docs-pulp.rhcloud.com'

SITE_ROOT = '~/app-root/repo/diy/'

# dict of {git repo: [list of package dirs containing setup.py]} that need to be installed
# for apidoc generation to work; only used for pulp 3+
APIDOC_PACKAGES = {
    'pulp': ['common', 'platform', 'plugin']
}


def main():
    # Parse the args
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="Build the docs for a given release.")
    opts = parser.parse_args()
    is_pulp3 = opts.release.startswith('3')

    configuration = builder.load_config(opts.release)

    # Get platform build version
    repo_list = builder.components(configuration)
    try:
        pulp_dict = list(filter(lambda x: x['name'] == 'pulp', repo_list))[0]
    except IndexError:
        raise RuntimeError("config file does not have an entry for 'pulp'")
    version = pulp_dict['version']

    if version.endswith('alpha'):
        build_type = 'nightly'
    elif version.endswith('beta'):
        build_type = 'testing'
    elif version.endswith('rc'):
        build_type = 'testing'
    else:
        build_type = 'ga'

    x_y_version = '.'.join(version.split('.')[:2])

    builder.ensure_dir(WORKING_DIR, clean=True)

    # use the version update scripts to check out git repos and ensure correct versions
    for component in repo_list:
        builder.clone_branch(component)

    # install any apidoc dependencies that exist for pulp 3 docs
    if is_pulp3:
        for repo, packages in APIDOC_PACKAGES.items():
            for package in packages:
                package_dir = os.path.join(WORKING_DIR, repo, package)
                if os.path.exists(package_dir):
                    subprocess.check_call(['python', 'setup.py', 'develop'], cwd=package_dir)

    plugins_dir = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'plugins'])
    builder.ensure_dir(plugins_dir)

    plugins_to_add = []
    for component in repo_list:
        if component['name'] == 'pulp':
            promote.update_versions(os.path.join(WORKING_DIR, 'pulp'), *version.split('-'))
            continue

        # build docs only for specific plugins
        if component.get('build_docs', True):
            plugins_to_add.append(component['name'])
            src = os.sep.join([WORKING_DIR, component['name'], 'docs'])
            dst = os.sep.join([plugins_dir, component['name']])
            os.symlink(src, dst)

    if not is_pulp3:
        # copy in the plugin_index.rst file eliminating plugins for which docs are not built
        src_plugin_index = 'docs/plugin_index.rst'
        dst_plugin_index = os.sep.join([plugins_dir, 'index.rst'])
        copy_content = True
        plugin_block_regex = re.compile(r'\.\. (_[a-z]+)_list_desc:')
        with open(src_plugin_index) as f_src, open(dst_plugin_index, 'w') as f_dst:
            for line in f_src:
                match = plugin_block_regex.search(line)
                if match:
                    plugin_name = 'pulp' + match.groups()[0]
                    copy_content = plugin_name in plugins_to_add
                if copy_content:
                    f_dst.write(line)

    # add plugin references to all_context_index.rst
    all_content_index_rst = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'all_content_index.rst'])
    with open(all_content_index_rst, 'a') as f_dst:
        for plugin_name in plugins_to_add:
            plugin_index_ref = '\n   %s' % os.sep.join(['plugins', plugin_name, 'index'])
            f_dst.write(plugin_index_ref)

    # make the _templates dir
    layout_dir = os.sep.join([WORKING_DIR, 'pulp', 'docs', '_templates'])
    os.makedirs(layout_dir)

    # copy in the layout.html file for analytics
    layout_html_path = os.sep.join([WORKING_DIR, 'pulp', 'docs', '_templates', 'layout.html'])
    copyfile('docs/layout.html', layout_html_path)

    # build the docs via the Pulp project itself
    print("Building the docs")
    docs_directory = os.sep.join([WORKING_DIR, 'pulp', 'docs'])
    make_command = ['make', 'html']
    exit_code = subprocess.call(make_command, cwd=docs_directory)
    if exit_code != 0:
        raise RuntimeError('An error occurred while building the docs.')

    # rsync the docs to the root if it's GA of latest
    if build_type == 'ga' and x_y_version == LATEST:
        local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
        remote_path_arg = '%s@%s:%s' % (USERNAME, HOSTNAME, SITE_ROOT)
        rsync_command = ['rsync', '-avzh', '--delete', '--exclude', 'en',
                         local_path_arg, remote_path_arg]
        exit_code = subprocess.call(rsync_command, cwd=docs_directory)
        if exit_code != 0:
            raise RuntimeError('An error occurred while pushing latest docs to OpenShift.')

    # rsync the nightly "master" docs to an unversioned "nightly" dir for
    # easy linking to in-development docs: /en/nightly/
    if build_type == 'nightly' and opts.release == 'master':
        local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
        remote_path_arg = '%s@%s:%sen/%s/' % (USERNAME, HOSTNAME, SITE_ROOT, build_type)
        path_option_arg = 'mkdir -p %sen/%s/ && rsync' % (SITE_ROOT, build_type)
        rsync_command = ['rsync', '-avzh', '--rsync-path', path_option_arg, '--delete',
                         local_path_arg, remote_path_arg]
        exit_code = subprocess.call(rsync_command, cwd=docs_directory)
        if exit_code != 0:
            raise RuntimeError('An error occurred while pushing nightly docs to OpenShift.')

    # rsync the docs to OpenShift
    local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
    remote_path_arg = '%s@%s:%sen/%s/' % (USERNAME, HOSTNAME, SITE_ROOT, x_y_version)
    if build_type != 'ga':
        remote_path_arg += build_type + '/'
        path_option_arg = 'mkdir -p %sen/%s/%s/ && rsync' % (SITE_ROOT, x_y_version, build_type)
        rsync_command = ['rsync', '-avzh', '--rsync-path', path_option_arg, '--delete',
                         local_path_arg, remote_path_arg]
    else:
        path_option_arg = 'mkdir -p %sen/%s/ && rsync' % (SITE_ROOT, x_y_version)
        rsync_command = ['rsync', '-avzh', '--rsync-path', path_option_arg, '--delete',
                         '--exclude', 'nightly', '--exclude', 'testing',
                         local_path_arg, remote_path_arg]
    exit_code = subprocess.call(rsync_command, cwd=docs_directory)
    if exit_code != 0:
        raise RuntimeError('An error occurred while pushing docs to OpenShift.')

    # rsync the robots.txt to OpenShift
    local_path_arg = 'docs/robots.txt'
    remote_path_arg = '%s@%s:%s' % (USERNAME, HOSTNAME, SITE_ROOT)
    scp_command = ['scp', local_path_arg, remote_path_arg]
    exit_code = subprocess.call(scp_command)
    if exit_code != 0:
        raise RuntimeError('An error occurred while pushing robots.txt to OpenShift.')

    # rsync the testrubyserver.rb to OpenShift
    local_path_arg = 'docs/testrubyserver.rb'
    remote_path_arg = '%s@%s:%s' % (USERNAME, HOSTNAME, SITE_ROOT)
    scp_command = ['scp', local_path_arg, remote_path_arg]
    exit_code = subprocess.call(scp_command)
    if exit_code != 0:
        raise RuntimeError('An error occurred while pushing testrubyserver.rb to OpenShift.')

    # add symlink for latest
    symlink_cmd = [
        'ssh',
        '%s@%s' % (USERNAME, HOSTNAME),
        'ln -sfn %sen/%s %sen/latest' % (SITE_ROOT, LATEST, SITE_ROOT)
    ]
    exit_code = subprocess.call(symlink_cmd)
    if exit_code != 0:
        raise RuntimeError("An error occurred while creating the 'latest' symlink "
                           "testrubyserver.rb to OpenShift.")


if __name__ == "__main__":
    main()
