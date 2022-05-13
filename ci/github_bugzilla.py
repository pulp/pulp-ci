#!/usr/bin/python3
"""
This module does a few things (not necessarily in this order):

0) Verify that all Bugzilla bugs which point to Github issues also have
Github issues pointing back to Bugzilla bugs. This script print a report of
changes made and any linking issues are found. If any link issues are
detected, a RuntimeError is raised so the caller will know an issue occurred.

1) For all Github issues that track Bugzilla bugs, ensure that the
Bugzilla external tracker description, status, and priority all mirror the
Github issue state. Also put a comment on the Bugzilla bug when changes are
made.

2) For each Bugzilla bug that corresponds with an upstream Pulp bug, ensure
that all e-mail addresses in the REQUIRED_CC are present on the cc list for
the Bugzilla bug. If they are not present add them. REQUIRED_CC is a list
of Bugzilla user emails stored as a constant in this module.

Requirements:
There are a few pip installable requirements:

    $ pip install requests python-bugzilla pygithub urllib3 pyopenssl

"""


import os
import re
from time import sleep

from bugzilla import RHBugzilla
from github import BadAttributeException, Github, UnknownObjectException
from requests.exceptions import ConnectionError, HTTPError, ReadTimeout
from xmlrpc.client import Fault


BUGZILLA_URL = "https://bugzilla.redhat.com"

DOWNSTREAM_CONTACTS = ["dkliban@redhat.com", "ggainey@redhat.com"]
REQUIRED_CC = ["rchan@redhat.com"] + DOWNSTREAM_CONTACTS


def get_bugzilla_connection(api_key):
    """
    Return the Bugzilla connection.

    :param api_key: The api_key to connect
    :type api_key: basestring

    :return: An instantiated Bugzilla connection object.
    """
    return RHBugzilla(url="%s/xmlrpc.cgi" % BUGZILLA_URL, api_key=api_key)


def get_github_connection(key):
    """
    Return the Github connection.

    :param key: The api key to connect with
    :type key: basestring

    :return: An instantiated Github connection object.
    """
    return Github(key)


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
    bugzilla_api_key = os.environ["BUGZILLA_API_KEY"]
    github_api_key = os.environ["GITHUB_API_TOKEN"]

    g = get_github_connection(github_api_key)
    BZ = get_bugzilla_connection(bugzilla_api_key)

    github_issues = []

    bz_label = g.get_repo("pulp/pulp_ansible").get_label("BZ")
    for repo in g.get_organization("pulp").get_repos():
        github_issues.extend(list(repo.get_issues(state="open", labels=[bz_label])))

    non_closed_bug_with_ext_tracker = (
        BUGZILLA_URL + "/buglist.cgi?bug_status=NEW&"
        "bug_status=ASSIGNED&bug_status=POST&bug_status=MODIFIED&bug_status=ON_DEV&"
        "bug_status=ON_QA&bug_status=VERIFIED&bug_status=RELEASE_PENDING&"
        "columnlist=priority%2Cbug_severity%2Cbug_status%2Cshort_desc%2Cchangeddate%2C"
        "component%2Ctarget_release%2Cassigned_to%2Creporter&f1=external_bugzilla.url&"
        "list_id=3309842&o1=substring&query_format=advanced&v1=pulp.plan.io"
    )
    query = BZ.url_to_query(non_closed_bug_with_ext_tracker)
    query["extra_fields"] = ["external_bugs"]

    links_issues_record = ""
    ext_bug_record = ""
    downstream_state_issue_record = ""
    downstream_changes = ""
    new_failed_qa_record = ""
    failed_qa_bugzillas = []
    not_found_bzs = []

    for issue in github_issues:
        if "github.com/pulp" not in issue.html_url:
            continue
        print(f"Processing github issue: {issue.html_url}")
        text = issue.body
        for comment in issue.get_comments():
            text = text + "\n\n" + comment.body
        if not text:
            not_found_bzs.append(issue.html_url)
            continue
        bugzillas = re.findall(r'.*bugzilla.redhat.com(.*)=([0-9]+)', text)
        for bugzilla_field in bugzillas:
            try:
                bug_id = int(bugzilla_field[1])
                print(f"  -> https://bugzilla.redhat.com/buglist.cgi?quicksearch={bug_id}")
            except IndexError:
                not_found_bzs.append(issue.html_url)
                continue
            links_back = False
            if bug_id in failed_qa_bugzillas:
                continue
            try:
                bug = BZ.getbug(bug_id)
            except Fault as e:
                if e.faultCode == 102:
                    print(("Bugzilla %s could not be accessed." % bug_id))
                    continue
                else:
                    raise
            except HTTPError as e:
                if e.response.status_code == 502:
                    # we constantly hit 502s from bugzilla.redhat.com and have filed tickets.
                    # response was that they couldn't fix it in the near future and to just retry.
                    sleep(1)
                    bug = BZ.getbug(bug_id)
                else:
                    raise

            for external_bug in bug.external_bugs:
                if str(external_bug["type"][
                    "description"
                ]).lower() == "github" and external_bug["ext_bz_bug_id"].endswith(f"/issues/{issue.number}"):
                    add_cc_list_to_bugzilla_bug(bug)
                    ext_params = {}
                    if external_bug["ext_description"] != issue.title:
                        ext_params["ext_description"] = issue.title
                    if str(external_bug["ext_status"]).lower() != issue.state.lower():
                        ext_params["ext_status"] = issue.state
                    if len(list(ext_params.keys())) > 0:
                        ext_bug_record += (
                            "Bugzilla bug %s updated from upstream bug %s "
                            "with %s\n" % (bug.id, issue.number, ext_params)
                        )
                        ext_params["ids"] = external_bug["id"]
                        BZ.update_external_tracker(**ext_params)
                        if "ext_status" in ext_params:
                            bug.addcomment(
                                "The Pulp upstream bug status is at %s. Updating the "
                                "external tracker on this bug." % issue.state
                            )
                    downstream_POST_plus = [
                        "POST",
                        "MODIFIED",
                        "ON_QA",
                        "VERIFIED",
                        "RELEASE_PENDING",
                        "CLOSED",
                    ]
                    downstream_ACCEPTABLE_resolution = [
                        "NOTABUG",
                        "WONTFIX",
                        "DEFERRED",
                        "WORKSFORME",
                    ]
                    if (
                        bug.status in downstream_POST_plus
                        and issue.state == "open"
                    ):
                        if bug.resolution not in downstream_ACCEPTABLE_resolution:
                            msg = (
                                "The downstream bug %s is at POST+ but the upstream "
                                "bug %s at POST-.\n" % (bug.id, issue.number)
                            )
                            downstream_state_issue_record += msg
                    links_back = True
            transition_to_closed = []
            for external_bug in bug.external_bugs:
                if external_bug["type"]["description"] == "Foreman Issue Tracker":
                    # If the bug has an external foreman issue, don't transition the BZ
                    transition_to_closed.append(False)
                if str(external_bug["type"]["description"]).lower() == "github":
                    if bug.status in ["NEW", "ASSIGNED"]:
                        if str(external_bug["ext_status"]).lower() == "closed":
                            if "FailedQA" in bug.cf_verified:
                                external_bug_repo, external_bug_id = external_bug["ext_bz_bug_id"].split("/issues/")
                                print(f"Processing external bug: https://github.com/{external_bug['ext_bz_bug_id']}.")

                                try:
                                    github_issue = g.get_repo(external_bug_repo).get_issue(int(external_bug_id))
                                except (ConnectionError, ReadTimeout):
                                    # we've experienced timeouts here so retry the connection
                                    g = get_github_connection(github_api_key)
                                    github_issue = g.get_repo(external_bug_repo).get_issue(int(external_bug_id))

                                try:
                                    needinfo_email = github_issue.assignee.email
                                    BZ.getuser(needinfo_email)
                                except BadAttributeException:
                                    # the upstream issue is unassigned
                                    user_has_no_bz = True
                                except Fault as e:
                                    if e.faultCode == 51:
                                        user_has_no_bz = True
                                    else:
                                        raise
                                else:
                                    user_has_no_bz = False

                                # If the Github user does not have a Bugzilla account, default
                                # to the downstream contacts for Pulp
                                if user_has_no_bz:
                                    needsinfo_contacts = DOWNSTREAM_CONTACTS
                                else:
                                    needsinfo_contacts = [needinfo_email]

                                # Don't set needsinfo for people who are already flagged
                                for flag in bug.flags:
                                    if (
                                        flag["name"] == "needinfo"
                                        and flag["requestee"] in needsinfo_contacts
                                    ):
                                        needsinfo_contacts = list(
                                            filter(
                                                lambda x: x != flag["requestee"],
                                                needsinfo_contacts,
                                            )
                                        )

                                if needsinfo_contacts:
                                    flags = []
                                    for contact in needsinfo_contacts:
                                        flags.append(
                                            {
                                                "name": "needinfo",
                                                "status": "?",
                                                "requestee": contact,
                                                "new": True,
                                            }
                                        )
                                    updates = BZ.build_update(
                                        status=bug.status, flags=flags
                                    )
                                    BZ.update_bugs(bug.id, updates)
                                    bug.addcomment(
                                        "Requesting needsinfo from upstream "
                                        "developer %s because the 'FailedQA' "
                                        "flag is set." % ", ".join(needsinfo_contacts)
                                    )

                                    msg = (
                                        "Bugzilla %s failed QA. Needinfo is set for %s."
                                        % (bug.id, ", ".join(needsinfo_contacts))
                                    )
                                    new_failed_qa_record += "%s\n" % msg
                                    print(msg)

                                failed_qa_bugzillas.append(bug.id)
                            else:
                                transition_to_closed.append(True)
                        else:
                            transition_to_closed.append(False)
            if not links_back:
                links_issues_record += (
                    "Github #%s -> Bugzilla %s, but Bugzilla %s does "
                    "not link back\n" % (issue.number, bug.id, bug.id)
                )
            if len(transition_to_closed) > 0 and all(transition_to_closed):
                msg = (
                    "All upstream Pulp bugs are at MODIFIED+. Moving this bug to POST."
                )
                bug.setstatus("POST", msg)
                downstream_changes += "Bugzilla %s was transitioned to POST\n" % bug.id

    BZ = get_bugzilla_connection(bugzilla_api_key)
    bugzilla_bugs = BZ.query(query)
    for bug in bugzilla_bugs:
        print(f"Processing bugzilla: https://bugzilla.redhat.com/buglist.cgi?quicksearch={bug.id}")
        for external_bug in bug.external_bugs:
            if str(external_bug["type"]["description"]).lower() == "github":
                add_cc_list_to_bugzilla_bug(bug)
                issue_id = None
                pull_id = None
                try:
                    if "issues" in external_bug["ext_bz_bug_id"]:
                        issue_repo, issue_id = external_bug["ext_bz_bug_id"].split("/issues/")
                        issue = g.get_repo(issue_repo).get_issue(int(issue_id))
                    elif "pull" in external_bug["ext_bz_bug_id"]:
                        issue_repo, pull_id = external_bug["ext_bz_bug_id"].split("/pull/")
                        issue = g.get_repo(issue_repo).get_pull(int(pull_id))
                except UnknownObjectException:
                    links_issues_record += (
                        "Bugzilla #%s -> Github %s, but Github %s does "
                        "not exist\n" % (bug.id, issue_id, issue_id)
                    )
                    continue
                except (ConnectionError, ReadTimeout):
                    # we've experienced timeouts here so retry the connection
                    g = get_github_connection(github_api_key)
                    if "issues" in external_bug["ext_bz_bug_id"]:
                        issue = g.get_repo(issue_repo).get_issue(int(issue_id))
                    elif "pull" in external_bug["ext_bz_bug_id"]:
                        issue = g.get_repo(issue_repo).get_pull(int(pull_id))
                if "github.com/pulp" not in issue.html_url:
                    continue
                text = issue.body
                for comment in issue.get_comments():
                    text = text + "\n\n" + comment.body
                if not text:
                    not_found_bzs.append(issue.html_url)
                    continue
                bugzillas = re.findall(r'.*bugzilla.redhat.com(.*)=([0-9]+)', text)
                for bugzilla_field in bugzillas:
                    try:
                        bug_id = int(bugzilla_field[1])
                        print(f"  -> https://bugzilla.redhat.com/buglist.cgi?quicksearch={bug_id}")
                    except IndexError:
                        not_found_bzs.append(issue.html_url)
                        continue
                    links_back = False
                    try:
                        if bug_id == bug.id:
                            links_back = True
                    except KeyError:
                        # If value isn't present this field is not linking back
                        continue
                    except ValueError:
                        # If value is present but empty this field is not linking back
                        continue
                    if not links_back:
                        links_issues_record += (
                            "Bugzilla #%s -> Github %s, but Github %s does "
                            "not link back\n" % (bug.id, issue.number, issue.number)
                        )

    if ext_bug_record != "":
        print("\nBugzilla Updates From Upstream")
        print("------------------------------")
        print(ext_bug_record)

    if downstream_changes != "":
        print("\nBugzilla Transitions to POST")
        print("----------------------------")
        print(downstream_changes)

    if links_issues_record != "":
        print("\nLink Issues")
        print("-----------")
        print(links_issues_record)

    if downstream_state_issue_record != "":
        print("\nDownstream State Issues")
        print("-----------------------")
        print(downstream_state_issue_record)

    if new_failed_qa_record != "":
        print("\nNew Bugzillas That Failed QA")
        print("----------------------------")
        print(new_failed_qa_record)

    if not_found_bzs:
        print("\nCouldn't find Bugzilla link on the following Github issues:")
        print("----------------------------")
        print(not_found_bzs)

    if (
        links_issues_record != ""
        or downstream_state_issue_record != ""
        or new_failed_qa_record
        or not_found_bzs
    ):
        # Raise an exception so the job fails and Jenkins will send e-mail
        raise RuntimeError("We need a human here")


if __name__ == "__main__":
    main()
