#!/usr/bin/env python2

"""Docker-focused client for pulp docker registry
"""

import argparse
import errno
import getpass
import os.path
import re
import subprocess
import tempfile


class Environment(object):
    """Host environment"""

    def __init__(self):
        """Environment defaults"""
        self.conf_dir = os.path.expanduser("~") + "/.pulp"
        self.conf_file = "admin.conf"
        self.user_cert = "user-cert.pem"
        #self.uploads_dir = "/run/docker_uploads"
        self.uploads_dir = "/tmp/docker_uploads"

    def setup(self):
        """Setup host environment directories and login if needed"""
        if not self.is_configured:
            print "Registry config file not found. Setting up environment."
            self.create_config()
        if self.selinux_enabled:
            self.set_context()
        if not self.is_loggedin:
            print "User certificate not found."
            self.login_user()

    @property
    def selinux_enabled(self):
        """is selinux either enforcing or permissive?"""
        try:
            out, err = subprocess.Popen(['getenforce'], stdout=subprocess.PIPE).communicate()
            if out.strip().lower() == 'disabled':
                return False
        except OSError, e:
            if e.errno == eerno.ENOENT:
                # command "getenforce" was not found, so we probably don't have selinux enabled.
                return False
            raise
        return True

    @property
    def is_configured(self):
        """Does the pulp configuration file exist?"""
        return os.path.isfile("%s/%s" % (self.conf_dir, self.conf_file))

    @property
    def is_loggedin(self):
        """Does the pulp user certificate exist?"""
        return os.path.isfile("%s/%s" % (self.conf_dir, self.user_cert))

    def create_config(self):
        """Create config dir, uploads dir and conf file"""
        print "Creating config file %s/%s" % (self.conf_dir, self.conf_file)
        if not os.path.exists(self.conf_dir):
            os.makedirs(self.conf_dir)
        if not os.path.exists(self.uploads_dir):
            print "Creating %s" % self.uploads_dir
            os.makedirs(self.uploads_dir)

        pulp_hostname = raw_input("Enter registry server hostname: ")
        while pulp_hostname is "":
            pulp_hostname = raw_input("Invalid hostname. Enter registry server hostname, e.g. registry.example.com: ")
        verify_ssl = raw_input("Verify SSL (requires CA-signed certificate) [False]: ") or "False"
        f = open("%s/%s" % (self.conf_dir, self.conf_file), "w")
        f.write("[server]\nhost = %s\nverify_ssl = %s\n" % (pulp_hostname, verify_ssl))
        f.close()

    def set_context(self):
        """Set SELinux context for dirs"""
        c1 = "sudo chcon -Rvt svirt_sandbox_file_t %s" % self.conf_dir
        proc = subprocess.Popen(c1.split(), stdout=subprocess.PIPE)
        proc.wait()
        c2 = "sudo chcon -Rv -u system_u -t svirt_sandbox_file_t %s" % self.uploads_dir
        proc = subprocess.Popen(c2.split(), stdout=subprocess.PIPE)
        proc.wait()

    def login_user(self):
        """Prompt user to login"""
        local_user = getpass.getuser()
        username = raw_input("Enter registry username [%s]: " % local_user) or local_user
        while username is "":
            username = raw_input("Invalid username. You must have a registry username to continue. If not known see system administrator: ")
        password = getpass.getpass("Enter registry password: ")
        while password is "":
            password = getpass.getpass("Password blank. Enter registry password: ")
        cmd = "login -u %s -p %s" % (username, password)
        c = Command(cmd)
        c.run(stdout=True)

    def logout_user(self):
        """Logout user"""
        cmd = "logout"
        c = Command(cmd)
        c.run(stdout=True)


class Pulp(object):
    """Construct pulp commands"""
    def __init__(self, args):
        self.args = args

    def parsed_args(self):
        """Logic to parse arguments"""
        cmd = []
        if self.args.mode == "create":
            git_str = ""
            if self.args.git_url:
                git_str = "--note git-url=%s" % self.args.git_url
            cmd.append("docker repo create --repo-registry-id %s --repo-id %s %s --redirect-url http://pulpapi/pulp/docker/%s/" %
                        (self.args.repo, self.repo_name(self.args.repo), git_str, self.repo_name(self.args.repo)))
        elif self.args.mode == "sync":
            cmd.append("docker repo create --repo-registry-id %s --repo-id %s --feed %s --upstream-name %s --validate True" %
                        (self.args.repo, self.repo_name(self.args.repo), self.args.sync_url, self.args.repo))
        elif self.args.mode == "delete":
            cmd.append("docker repo delete --repo-id %s" %
                        self.repo_name(self.args.repo))
        elif self.args.mode == "push":
            temp_file = self.docker_save()
            cmd.append("docker repo create --repo-registry-id %s --repo-id %s --redirect-url http://pulpapi/pulp/docker/%s/" %
                        (self.args.repo, self.repo_name(self.args.repo), self.repo_name(self.args.repo)))
            cmd.append("docker repo uploads upload --repo-id %s --file %s" %
                        (self.repo_name(self.args.repo), temp_file))
            cmd.append("docker repo publish run --repo-id %s" %
                        self.repo_name(self.args.repo))
        elif self.args.mode == "history":
            cmd.append("tasks list")
        elif self.args.mode == "list":
            if self.args.list_item != "repos":
                cmd.append("docker repo images -d --repo-id %s" %
                            self.repo_name(self.args.list_item))
            else:
                cmd.append("docker repo list --details")
        elif self.args.mode == "pulp":
            cmd.append(self.args.pulp_cmd)
        return cmd

    def repo_name(self, repo):
        """Returns pulp-friendly repository name without slash"""
        return repo.replace("/", "-")

    def docker_save(self):
        """Saves docker image, returns temp file"""
        env = Environment()
        temp_file = tempfile.NamedTemporaryFile(mode='w+b', dir=env.uploads_dir, suffix=".tar", delete=False)
        cmd = "sudo docker save -o %s %s" % (temp_file.name, self.args.repo)
        print "Saving docker file as %s" % temp_file.name
        subprocess.call(cmd.split())
        return temp_file.name

    def execute(self):
        """Send parsed command to command class"""
        for cmd in self.parsed_args():
            c = Command(cmd)
            self.format_output(c.run())

    def format_output(self, output):
        """Format output of commands"""
        if self.args.mode == "list":
            if self.args.list_item == "repos":
                regex = re.compile(r'repo-registry-id:(.+$)', re.I)
            else:
                regex = re.compile(r'image id:(.+$)', re.I)
            for out in output.stdout:
                line = regex.search(out)
                if line:
                    print line.group(1).strip()
        else:
            for out in output.stdout:
                print out.strip()


class Command(object):
    """Build and run command"""
    def __init__(self, cmd):
        self.cmd = cmd

    @property
    def base_cmd(self):
        """Construct base pulp admin container command"""
        env = Environment()
        conf_dir = env.conf_dir
        uploads_dir = env.uploads_dir
        return "sudo docker run --rm --link pulpapi:pulpapi -t -v %(conf_dir)s:/root/.pulp -v %(uploads_dir)s:%(uploads_dir)s pulp/admin-client pulp-admin" % vars()

    def run(self, stdout=None):
        """Run command"""
        cmd = "%s %s" % (self.base_cmd, self.cmd)
        cmd = cmd.split()
        if stdout:
            subprocess.call(cmd)
        else:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            proc.wait()
            return proc


def parse_args():
    """Parse arguments"""
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(help='sub-command help', dest='mode')
    push_parser = subparsers.add_parser('push', help='Push a repository to the registry')
    push_parser.add_argument('repo',
                       metavar='MY/APP',
                       help='Repository name')
    create_parser = subparsers.add_parser('create', help='Create an empty repository, optionally tag with Dockerfile git repo')
    create_parser.add_argument('repo',
                       metavar='MY/APP',
                       help='Repository name')
    create_parser.add_argument('-g', '--git-url',
                       metavar='http://git.example.com/repo/myapp',
                       help='URL of Dockerfile git repository')
    create_parser.add_argument('-b', '--git-branch',
                       metavar='BRANCH',
                       help='git branch of Dockerfile repository')
    #create_parser.add_argument('-t', '--git-tag',
    #                   metavar='TAG',
    #                   help='git tag of Dockerfile repository')
    sync_parser = subparsers.add_parser('sync', help='Sync a repository from another registry')
    sync_parser.add_argument('repo',
                       metavar='MY/APP',
                       help='Repository name')
    sync_parser.add_argument('sync_url',
                       metavar='https://registry.access.redhat.com',
                       help='Base URL of registry to sync from')
    delete_parser = subparsers.add_parser('delete', help='repository')
    delete_parser.add_argument('repo',
                       metavar='MY/APP',
                       help='Repository name')
    list_parser = subparsers.add_parser('list', help='List registry repos or images in a repo')
    list_parser.add_argument('list_item',
                       metavar='repos|MY/APP',
                       help='Repos or repo images')
    subparsers.add_parser('history', help='Display history of registry tasks')
    login_parser = subparsers.add_parser('login', help='Login to pulp registry')
    login_parser.add_argument('-u', '--username',
                       metavar='USERNAME',
                       help='Pulp registry username')
    login_parser.add_argument('-p', '--password',
                       metavar='PASSWORD',
                       help='Pulp registry password')
    subparsers.add_parser('logout', help='Logout of the pulp registry')
    pulp_parser = subparsers.add_parser('pulp', help='pulp-admin commands')
    pulp_parser.add_argument('pulp_cmd',
                       metavar='"PULP COMMAND FOO BAR"',
                       help='pulp-admin command string')
    return parser.parse_args()


def main():
    """Entrypoint for script"""
    args = parse_args()
    env = Environment()
    if args.mode in "logout":
        env.logout_user()
        exit(0)
    env.setup()
    if args.mode in "login":
        exit(0)
    p = Pulp(args)
    p.execute()

if __name__ == '__main__':
    main()

