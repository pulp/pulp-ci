#!/usr/bin/python3
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
There are a few pip installable requirements:

    $ pip install requests python-bugzilla python-redmine urllib3 pyopenssl

"""


import os
from time import sleep

from bugzilla import RHBugzilla
from redminelib import Redmine, exceptions
from requests.exceptions import ConnectionError, HTTPError, ReadTimeout
from xmlrpc.client import Fault


BUGZILLA_URL = "https://bugzilla.redhat.com"
REDMINE_URL = "https://pulp.plan.io"

DOWNSTREAM_CONTACTS = ["bmbouter@redhat.com", "ipanova@redhat.com"]
REQUIRED_CC = ["rchan@redhat.com"] + DOWNSTREAM_CONTACTS


def get_bugzilla_connection(api_key):
    """
    Return the Bugzilla connection.

    :param api_key: The api_key to connect
    :type api_key: basestring

    :return: An instantiated Bugzilla connection object.
    """
    return RHBugzilla(url="%s/xmlrpc.cgi" % BUGZILLA_URL, api_key=api_key)


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
    bugzilla_api_key = os.environ["BUGZILLA_API_KEY"]
    redmine_api_key = os.environ["REDMINE_API_KEY"]

    redmine = get_redmine_connection(redmine_api_key)
    BZ = get_bugzilla_connection(bugzilla_api_key)

    redmine_issues = [issue for issue in redmine.issue.filter(query_id=24)]

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
    bugzilla_bugs = BZ.query(query)

    links_issues_record = ""
    ext_bug_record = ""
    downstream_state_issue_record = ""
    downstream_changes = ""
    new_failed_qa_record = ""
    failed_qa_bugzillas = []

    for issue in redmine_issues:
        print(f"Processing {issue.id}.")
        bugzilla_field = issue.custom_fields.get(32)  # 32 is the 'Bugzillas' field
        if bugzilla_field["value"] == "":
            continue
        for bug_id in [int(id_str) for id_str in bugzilla_field["value"].split(",")]:
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
                if external_bug["type"][
                    "description"
                ] == "Pulp Redmine" and external_bug["ext_bz_bug_id"] == str(issue.id):
                    add_cc_list_to_bugzilla_bug(bug)
                    ext_params = {}
                    if external_bug["ext_description"] != issue.subject:
                        ext_params["ext_description"] = issue.subject
                    if external_bug["ext_status"] != issue.status.name:
                        ext_params["ext_status"] = issue.status.name
                    if external_bug["ext_priority"] != issue.priority.name:
                        ext_params["ext_priority"] = issue.priority.name
                    if len(list(ext_params.keys())) > 0:
                        ext_bug_record += (
                            "Bugzilla bug %s updated from upstream bug %s "
                            "with %s\n" % (bug.id, issue.id, ext_params)
                        )
                        ext_params["ids"] = external_bug["id"]
                        BZ.update_external_tracker(**ext_params)
                        if "ext_status" in ext_params:
                            bug.addcomment(
                                "The Pulp upstream bug status is at %s. Updating the "
                                "external tracker on this bug." % issue.status.name
                            )
                        if "ext_priority" in ext_params:
                            bug.addcomment(
                                "The Pulp upstream bug priority is at %s. Updating the "
                                "external tracker on this bug." % issue.priority.name
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
                    upstream_POST_minus = ["NEW", "ASSIGNED", "POST"]
                    if (
                        bug.status in downstream_POST_plus
                        and issue.status.name in upstream_POST_minus
                    ):
                        if bug.resolution not in downstream_ACCEPTABLE_resolution:
                            msg = (
                                "The downstream bug %s is at POST+ but the upstream "
                                "bug %s at POST-.\n" % (bug.id, issue.id)
                            )
                            downstream_state_issue_record += msg
                    links_back = True
            transition_to_post = []
            for external_bug in bug.external_bugs:
                if external_bug["type"]["description"] == "Foreman Issue Tracker":
                    # If the bug has an external foreman issue, don't transition the BZ
                    transition_to_post.append(False)
                if external_bug["type"]["description"] == "Pulp Redmine":
                    if bug.status in ["NEW", "ASSIGNED"]:
                        if external_bug["ext_status"] in [
                            "MODIFIED",
                            "ON_QA",
                            "VERIFIED",
                            "CLOSED - CURRENTRELEASE",
                            "CLOSED - COMPLETE",
                            "CLOSED - DUPLICATE",
                        ]:
                            if "FailedQA" in bug.cf_verified:
                                external_bug_id = external_bug["ext_bz_bug_id"]
                                print(f"Processing external bug {external_bug_id}.")

                                try:
                                    redmine_issue = redmine.issue.get(external_bug_id)
                                except (ConnectionError, ReadTimeout):
                                    # we've experienced timeouts here so retry the connection
                                    redmine = get_redmine_connection(redmine_api_key)
                                    redmine_issue = redmine.issue.get(external_bug_id)

                                try:
                                    redmine_user_id = redmine_issue.assigned_to.id
                                    needinfo_email = redmine.user.get(redmine_user_id).mail
                                    BZ.getuser(needinfo_email)
                                except exceptions.ResourceAttrError:
                                    # the upstream issue is unassigned
                                    user_has_no_bz = True
                                except Fault as e:
                                    if e.faultCode == 51:
                                        user_has_no_bz = True
                                    else:
                                        raise
                                else:
                                    user_has_no_bz = False

                                # If the Redmine user does not have a Bugzilla account, default
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
                                transition_to_post.append(True)
                        else:
                            transition_to_post.append(False)
            if not links_back:
                links_issues_record += (
                    "Redmine #%s -> Bugzilla %s, but Bugzilla %s does "
                    "not link back\n" % (issue.id, bug.id, bug.id)
                )
            if len(transition_to_post) > 0 and all(transition_to_post):
                msg = (
                    "All upstream Pulp bugs are at MODIFIED+. Moving this bug to POST."
                )
                bug.setstatus("POST", msg)
                downstream_changes += "Bugzilla %s was transitioned to POST\n" % bug.id

    for bug in bugzilla_bugs:
        for external_bug in bug.external_bugs:
            if external_bug["type"]["description"] == "Pulp Redmine":
                add_cc_list_to_bugzilla_bug(bug)
                issue_id = external_bug["ext_bz_bug_id"]
                try:
                    issue = redmine.issue.get(issue_id)
                except exceptions.ResourceNotFoundError as e:
                    links_issues_record += (
                        "Bugzilla #%s -> Redmine %s, but Redmine %s does "
                        "not exist\n" % (bug.id, issue_id, issue_id)
                    )
                    continue
                links_back = False
                bugzilla_field = issue.custom_fields.get(
                    32
                )  # 32 is the 'Bugzillas' field
                if bugzilla_field["value"]:
                    bug_list = [
                        int(id_str) for id_str in bugzilla_field["value"].split(",")
                    ]
                    for bug_id in bug_list:
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
                        "Bugzilla #%s -> Redmine %s, but Redmine %s does "
                        "not link back\n" % (bug.id, issue.id, issue.id)
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

    if (
        links_issues_record != ""
        or downstream_state_issue_record != ""
        or new_failed_qa_record
    ):
        # Raise an exception so the job fails and Jenkins will send e-mail
        raise RuntimeError("We need a human here")


if __name__ == "__main__":
    main()
