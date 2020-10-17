import os
import re
from datetime import datetime, timedelta

from github import Github
from github.GithubException import UnknownObjectException
from redminelib import Redmine

ORG = "pulp"
REPOS = [
    "pulpcore",
    "pulp_file",
    "pulp_rpm",
    "pulp_container",
    "pulp_ansible",
    "pulp_deb",
    "pulp-certguard",
    "pulp_installer",
    "pulp-oci-images",
    "pulp-operator",
    "plugin_template",
    "pulp-cli",
]
SINCE = datetime.utcnow() - timedelta(hours=1)
KEYWORDS = ["fixes", "closes", "re", "ref"]
PR_STATUS = 3  # POST

# redmine
REDMINE_URL = "https://pulp.plan.io"
REDMINE_KEY = os.environ["REDMINE_API_KEY"]

# github
GITHUB_USER = 'pulpbot'
GITHUB_TOKEN = os.environ["GITHUB_API_TOKEN"]


def user_comment(issue, user=GITHUB_USER):
    """Find the first comment by a user for an issue."""
    for comment in issue.get_comments():
        if comment.user.login == user:
            return comment


if not REDMINE_KEY or not GITHUB_TOKEN:
    print("Missing redmine and/or github api key.")
    exit(0)

redmine = Redmine(REDMINE_URL, key=REDMINE_KEY)
g = Github(GITHUB_TOKEN)

regex = r"(?:{keywords})[\s:]+#(\d+)".format(keywords=("|").join(KEYWORDS))
pattern = re.compile(regex, re.IGNORECASE)

for repo in REPOS:
    print(f"\n\nProcessing repository {repo}")
    grepo = g.get_repo(f"{ORG}/{repo}")
    issues = grepo.get_issues(since=SINCE)

    for issue in issues:
        print(f"Processing issue {issue.number}")

        # check if we've seen this PR already
        if user_comment(issue):
            print(f"Issue {issue.number} already processed. Skipping.")
            continue

        # check if our bot opened this issue
        if issue.user.login == GITHUB_USER:
            continue

        pr = issue.as_pull_request()

        r_issues = []
        for commit in pr.get_commits():
            message = commit.commit.message
            r_issues.extend(pattern.findall(message))

        # UPDATE THE ISSUE IN REDMINE

        needs_cherry_pick = False

        if not r_issues:
            print(f"Issue {issue.number} has no attached redmine ticket.")
            comment = (
                "WARNING!!! This PR is not attached to an issue. In most cases this is not advisable. "
                "Please see [our PR docs](http://docs.pulpproject.org/contributing/git.html#commit-message)"
                " for more information about how to attach this PR to an issue."
            )
        else:
            print(f"Found redmine ticket(s) for issue {issue.number}.")
            comment = ""
            for issue_num in r_issues:
                r_issue = redmine.issue.get(issue_num)

                if r_issue.tracker.name == "Issue":
                    needs_cherry_pick = True

                if r_issue.status.id <= PR_STATUS:
                    redmine.issue.update(issue_num, status_id=3, notes=f"PR: {pr.html_url}")
                    comment += f"Attached issue: {r_issue.url}\n\n"
                else:
                    comment += f"Warning: Issue [#{r_issue.id}]({r_issue.url}) is not at NEW/ASSIGNED/POST.\n\n"
                    redmine.issue.update(issue_num, notes=f"PR: {pr.html_url}")

        grepo.get_issue(pr.number).create_comment(comment)

        # ADD LABELS

        if needs_cherry_pick:
            print(f"Issue {issue.number} has attached bug. Adding cherry pick label.")
            try:
                label = grepo.get_label("Needs Cherry Pick")
            except UnknownObjectException:
                print("No cherry pick label found.")
                continue

            labels = pr.labels + [label]
            grepo.get_issue(pr.number).edit(labels=[lbl.name for lbl in labels])
