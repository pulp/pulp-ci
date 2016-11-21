"""
This module does a few things (not necessarily in this order):

0) Verify that all Bugzilla bugs which point to a Redmine issues also have
Redmine issues pointing back to Bugzilla bugs. This script print a report of
changes made and any linking issues are found. If any link issues are
detected, a RuntimeError is raised so the caller will know an issue occurred.

1) For all Redmine issues that track Bugzilla bugs, ensure that the
Bugzilla external tracker description, status, and priority all mirror the
Redmine issue state. Also put a comment on the Bugzilla bug when changes are
made.

2) For each Bugzilla bug that corresponds with an upstream Pulp bug, ensure
that all e-mail addresses in the REQUIRED_CC are present on the cc list for
the Bugzilla bug. If they are not present add them. REQUIRED_CC is a list
of Bugzilla user emails stored as a constant in this module.

Requirements:
The Redmine and Bugzilla credentials are expected from to be read from a
file in ini format. See the example below. The location of this file is set
by the REDMINE_BUGZILLA_CONF environment variable.

<SNIP>
[bugzilla]
username = XXXX
password = XXXX

[redmine]
key = XXXX
</SNIP>
"""


import ConfigParser
import os

from bugzilla.rhbugzilla import RHBugzilla
from redmine import Redmine
import urllib3.contrib.pyopenssl
import xmlrpclib

# Here due to InsecurePlatformWarning
# https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning
urllib3.contrib.pyopenssl.inject_into_urllib3()


BUGZILLA_URL = 'https://bugzilla.redhat.com'
REDMINE_URL = 'https://pulp.plan.io'

REQUIRED_CC = ['mhrivnak@redhat.com', 'bbouters@redhat.com']


def get_bugzilla_connection(user, password):
    """
    Return the Bugzilla connection.

    :param user: The username to connect with
    :type user: basestring
    :param password: The password to connect with
    :type password: basestring

    :return: An instantiated Bugzilla connection object.
    """
    return RHBugzilla(url='%s/xmlrpc.cgi' % BUGZILLA_URL, user=user, password=password)


def get_redmine_connection(key):
    """
    Return the Redmine connection.

    :param key: The api key to connect with
    :type key: basestring

    :return: An instantiated Redmine connection object.
    """
    return Redmine(REDMINE_URL, key=key)


def add_cc_list_to_bugzilla_bug(bug):
    """
    Ensure that all users in REQUIRED_CC are in the cc list of the bug.

    :param bug: The Bugzilla bug to have its cc list members ensured.
    :type bug: bugzilla.bug
    """
    for pulp_cc_username in REQUIRED_CC:
        if pulp_cc_username not in bug.cc:
            bug.addcc(pulp_cc_username)


def main():
    config = ConfigParser.ConfigParser()
    config.read(os.environ['REDMINE_BUGZILLA_CONF'])

    username = config.get('bugzilla', 'username')
    password = config.get('bugzilla', 'password')
    key = config.get('redmine', 'key')

    redmine = get_redmine_connection(key)
    BZ = get_bugzilla_connection(username, password)

    redmine_issues = [issue for issue in redmine.issue.filter(query_id=24)]

    non_closed_bug_with_ext_tracker = BUGZILLA_URL + '/buglist.cgi?bug_status=NEW&' \
        'bug_status=ASSIGNED&bug_status=POST&bug_status=MODIFIED&bug_status=ON_DEV&' \
        'bug_status=ON_QA&bug_status=VERIFIED&bug_status=RELEASE_PENDING&' \
        'columnlist=priority%2Cbug_severity%2Cbug_status%2Cshort_desc%2Cchangeddate%2C' \
        'component%2Ctarget_release%2Cassigned_to%2Creporter&f1=external_bugzilla.url&' \
        'list_id=3309842&o1=substring&query_format=advanced&v1=pulp.plan.io'
    bugzilla_bugs = BZ.query(RHBugzilla.url_to_query(non_closed_bug_with_ext_tracker))

    links_issues_record = ''
    ext_bug_record = ''

    for issue in redmine_issues:
        for custom_field in issue.custom_fields.resources:
            if custom_field['name'] == 'Bugzillas':
                if custom_field['value'] == '':
                    continue
                for bug_id in [int(id_str) for id_str in custom_field['value'].split(',')]:
                    links_back = False
                    try:
                        bug = BZ.getbug(bug_id)
                    except xmlrpclib.Fault as e:
                        if e.faultCode == 102:
                            print 'Bugzilla %s could not be accessed.' % bug_id
                            continue
                        else:
                            raise
                    for external_bug in bug.external_bugs:
                        if external_bug['type']['description'] == 'Pulp Redmine' and \
                                        external_bug['ext_bz_bug_id'] == str(issue.id):
                            add_cc_list_to_bugzilla_bug(bug)
                            ext_params = {}
                            if external_bug['ext_description'] != issue.subject:
                                ext_params['ext_description'] = issue.subject
                            if external_bug['ext_status'] != issue.status.name:
                                ext_params['ext_status'] = issue.status.name
                            if external_bug['ext_priority'] != issue.priority.name:
                                ext_params['ext_priority'] = issue.priority.name
                            if len(ext_params.keys()) > 0:
                                ext_bug_record += 'Bugzilla bug %s updated from upstream bug %s with ' \
                                                  '%s\n' % (bug.id, issue.id, ext_params)
                                ext_params['ids'] = external_bug['id']
                                BZ.update_external_tracker(**ext_params)
                                if 'ext_status' in ext_params:
                                    bug.addcomment(
                                        'The Pulp upstream bug status is at %s. Updating the external '
                                        'tracker on this bug.' % issue.status.name)
                                if 'ext_priority' in ext_params:
                                    bug.addcomment(
                                        'The Pulp upstream bug priority is at %s. Updating the '
                                        'external tracker on this bug.' % issue.priority.name)
                            links_back = True
                    if not links_back:
                        links_issues_record += 'Redmine #%s -> Bugzilla %s, but Bugzilla %s does not ' \
                                           'link back\n' % (issue.id, bug.id, bug.id)

    for bug in bugzilla_bugs:
        for external_bug in bug.external_bugs:
                if external_bug['type']['description'] == 'Pulp Redmine':
                    add_cc_list_to_bugzilla_bug(bug)
                    issue_id = external_bug['ext_bz_bug_id']
                    issue = redmine.issue.get(issue_id)
                    links_back = False
                    for custom_field in issue.custom_fields.resources:
                        if custom_field['name'] == 'Bugzillas' and custom_field['value']:
                            for bug_id in [int(id_str) for id_str in custom_field['value'].split(',')]:
                                try:
                                    if bug_id == bug.id:
                                        links_back = True
                                except KeyError:
                                    # If value isn't present this field is not linking back so continue
                                    continue
                                except ValueError:
                                    # If value is present but empty this field is not linking back
                                    continue
                    if not links_back:
                        links_issues_record += 'Bugzilla #%s -> Redmine %s, but Redmine %s does ' \
                                               'not link back\n' % (bug.id, issue.id, issue.id)

    if ext_bug_record != '':
        print '\nBugzilla Updates From Upstream'
        print '------------------------------'
        print ext_bug_record

    if links_issues_record != '':
        print '\nLink Issues'
        print '-----------'
        print links_issues_record
        # Raise an exception so the job fails and Jenkins will send e-mail
        raise RuntimeError('Upstream/Downstream Link issues are detected')


if __name__ == '__main__':
    main()
