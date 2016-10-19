#!/usr/bin/env python2

import argparse
import subprocess
import sys
import os
from shutil import copyfile

import yaml

from lib import builder
from lib.builder import WORKING_DIR


LATEST = '2.10'

USERNAME = '57600fb10c1e664383000229'
HOSTNAME = 'docs-pulp.rhcloud.com'

SITE_ROOT = '~/app-root/repo/diy/'


def get_components(configuration):
    # Get the components from the yaml file
    repos = configuration['repositories']
    for component in repos:
        yield component


def load_config(config_name):
    # Get the config
    config_file = os.path.join(os.path.dirname(__file__),
                               'config', 'releases', '%s.yaml' % config_name)
    if not os.path.exists(config_file):
        print("Error: %s not found. " % config_file)
        sys.exit(1)
    with open(config_file, 'r') as config_handle:
        config = yaml.safe_load(config_handle)
    return config

def main():
    # Parse the args
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="Build the docs for a given release.")
    opts = parser.parse_args()

    configuration = load_config(opts.release)

    # Get platform build version
    repo_list = configuration['repositories']
    try:
        pulp_dict = filter(lambda x: x['name'] == 'pulp', repo_list)[0]
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

    print "Getting git repos"
    for component in get_components(configuration):
        #clone the repos
        branch_name = component['git_branch']
        print "Cloning from github: %s" % component.get('git_url')
        print "Switching to branch %s" % branch_name
        clone_command = ['git', 'clone', component.get('git_url'), '--branch', branch_name]
        exit_code = subprocess.call(clone_command, cwd=WORKING_DIR)
        if exit_code != 0:
            raise RuntimeError('An error occurred while cloning the repo.')

    plugins_dir = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'plugins'])
    builder.ensure_dir(plugins_dir)

    for component in get_components(configuration):
        if component['name'] == 'pulp':
            continue

        src = os.sep.join([WORKING_DIR, component['name'], 'docs'])
        dst = os.sep.join([plugins_dir, component['name']])
        os.symlink(src, dst)

    # copy in the pulp_index.rst file
    src_path = 'docs/pulp_index.rst'
    pulp_index_rst = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'index.rst'])
    copyfile(src_path, pulp_index_rst)

    # copy in the plugin_index.rst file
    plugin_index_rst = os.sep.join([plugins_dir, 'index.rst'])
    copyfile('docs/plugin_index.rst', plugin_index_rst)

    # copy in the all_content_index.rst file
    all_content_index_rst = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'all_content_index.rst'])
    copyfile('docs/all_content_index.rst', all_content_index_rst)

    # make the _templates dir
    layout_dir = os.sep.join([WORKING_DIR, 'pulp', 'docs', '_templates'])
    os.makedirs(layout_dir)

    # copy in the layout.html file for analytics
    layout_html_path = os.sep.join([WORKING_DIR, 'pulp', 'docs', '_templates', 'layout.html'])
    copyfile('docs/layout.html', layout_html_path)

    # build the docs via the Pulp project itself
    print("Building the docs")
    docs_directory = os.sep.join([WORKING_DIR, 'pulp', 'docs'])
    make_command = ['make', 'html', 'SPHINXOPTS=-Wn']
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
            raise RuntimeError('An error occurred while pushing docs to OpenShift.')

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
