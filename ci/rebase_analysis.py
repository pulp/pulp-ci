#!/usr/bin/python2
"""
Determines what known downstream bugs are missing if a rebase is done to a given upstream release.

For each Satellite6 Bugzilla with an external Pulp bug, determine the earliest upstream x.y.latest
release that fixes that bug. x.y.latest is used assuming that Satellite would only rebase onto the
latest z stream which is expected to be the most stable.

The report produced has the format as follows:

    upstream version, downstream bugs missing count, link to bugzilla showing these bugs
    2.8.7, 142, https://bugzilla.redhat.com/buglist.cgi?quicksearch=1377195,1377186
    2.9.3, 110,https://bugzilla.redhat.com/buglist.cgi?quicksearch=1377113,1377912

To determine the upstream version that fixes a given Bugzilla, pulp.plan.io is queried for the
'Target Platform Release' field. In the case where a Bugzilla is associated with multiple upstream
pulp.plan.io issues, the highest version is used. It is assumed that every later release contains
all fixes and features from previous releases. This assumption applies to both later releases within
a z-stream and also later y releases.

Requirements:
There are a few pip installable requirements:

    $ pip install semantic_version python-bugzilla python-redmine

The Redmine and Bugzilla credentials are expected from to be read from a
file in ini format. See the example below. The location of this file is set
by the REDMINE_BUGZILLA_CONF environment variable.

For example `export REDMINE_BUGZILLA_CONF=~/Documents/redmine_bugzilla.ini`

<SNIP>
[bugzilla]
username = XXXX
password = XXXX

[redmine]
key = XXXX
</SNIP>
"""

from collections import defaultdict
import ConfigParser
import os

from bugzilla.rhbugzilla import RHBugzilla
import semantic_version
from redmine_bugzilla import BUGZILLA_URL, get_redmine_connection, get_bugzilla_connection


MINIMUM_VERSION = '2.9.0'


def main():
    config = ConfigParser.ConfigParser()
    config.read(os.environ['REDMINE_BUGZILLA_CONF'])

    username = config.get('bugzilla', 'username')
    password = config.get('bugzilla', 'password')
    key = config.get('redmine', 'key')

    redmine = get_redmine_connection(key)
    BZ = get_bugzilla_connection(username, password)

    bug_with_ext_tracker = \
        BUGZILLA_URL + '/buglist.cgi?classification=Red%20Hat&columnlist=priority%2Cbug_severity' \
                       '%2Cbug_status%2Cshort_desc%2Cchangeddate%2Ccomponent%2Ctarget_release%2C' \
                       'assigned_to%2Creporter&f1=external_bugzilla.url&list_id=7254713&o1=' \
                       'substring&product=Red%20Hat%20Satellite%206&query_format=advanced&' \
                       'resolution=---&resolution=CURRENTRELEASE&resolution=RAWHIDE&resolution=' \
                       'ERRATA&resolution=NEXTRELEASE&resolution=INSUFFICIENT_DATA&resolution=EOL' \
                       '&v1=pulp.plan.io'
    bugzilla_bugs = BZ.query(RHBugzilla.url_to_query(bug_with_ext_tracker))

    upstream_issues_checked_memo = {}  # A memo allowing us to never check an issue twice

    all_BZs = set()
    BZs_fixed_by_version = defaultdict(lambda : set())

    for i, bug in enumerate(bugzilla_bugs):
        # if i == 20:
        #     break
        all_BZs.add(bug.id)
        bug = BZ.getbug(bug.id)
        upstream_associated_issue_numbers = []
        for external_bug in bug.external_bugs:
            if external_bug['type']['description'] == 'Pulp Redmine':
                upstream_associated_issue_numbers.append(int(external_bug['ext_bz_bug_id']))

        upstream_fixed_versions_for_bz = []
        for upstream_id in upstream_associated_issue_numbers:

            # Check the memo to see if we already know the fix version
            if upstream_id in upstream_fixed_versions_for_bz:
                if upstream_fixed_versions_for_bz[upstream_id] != u'':
                    # We already know the upstream version with the fix available
                    upstream_fixed_versions_for_bz.append(
                        upstream_fixed_versions_for_bz[upstream_id]
                    )
                    all_BZs.add(bug.id)
                # The memo info was used so we can move on to the next upstream issue to check
                continue

            upstream_issue = redmine.issue.get(upstream_id)

            # Issues in 'External' are not actual issues so they should be ignored
            if upstream_issue.project.name == u'External':
                # Never check an upstream issue twice
                upstream_issues_checked_memo[upstream_id] = u''
                continue

            platform_release_field = upstream_issue.custom_fields.get(4)  # 'Platform Release' field

            # Never check an upstream issue twice
            upstream_issues_checked_memo[upstream_id] = platform_release_field[u'value']

            if platform_release_field[u'value'] != u'':
                upstream_fixed_versions_for_bz.append(platform_release_field[u'value'])
                all_BZs.add(bug.id)

        if upstream_fixed_versions_for_bz != []:
            fix_in = max([semantic_version.Version(v) for v in upstream_fixed_versions_for_bz])
            BZs_fixed_by_version[str(fix_in)].add(bug.id)

    upstream_versions = [semantic_version.Version(v) for v in BZs_fixed_by_version.keys()]
    upstream_versions.sort()  # Ensure in increasing order
    BZs_fixed_list = [BZs_fixed_by_version[str(v)] for v in upstream_versions]

    for i in range(1, len(BZs_fixed_list)):
        BZs_fixed_list[i] = BZs_fixed_list[i - 1] | BZs_fixed_list[i]

    for i, version in enumerate(upstream_versions):
        BZs_fixed_by_version[str(version)] = BZs_fixed_list[i]

    BZs_missing_by_version = {}
    for version, bugs in BZs_fixed_by_version.iteritems():
        BZs_missing_by_version[version] = all_BZs - BZs_fixed_by_version[version]

    minimum_version = semantic_version.Version(MINIMUM_VERSION)
    for v in upstream_versions:
        if v < minimum_version:
            continue
        bugs_in_this_version = BZs_missing_by_version[str(v)]
        print '%s, %s, https://bugzilla.redhat.com/buglist.cgi?quicksearch=%s' % (
            v, len(bugs_in_this_version), ','.join([str(i) for i in bugs_in_this_version])
        )


if __name__ == '__main__':
    main()
