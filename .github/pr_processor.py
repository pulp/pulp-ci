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
AUTO_MERGE_REPOS = [
    "pulpcore"
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

regex = r"(?:{keywords})[\s:]+#(\d+)".format(keywords=("|").join(KEYWORDS))
pattern = re.compile(regex)

if not REDMINE_KEY or not GITHUB_TOKEN:
    print("Missing redmine and/or github api key.")
    exit(0)

redmine = Redmine(REDMINE_URL, key=REDMINE_KEY)
g = Github(GITHUB_TOKEN)


def user_comment(issue, user=GITHUB_USER):
    """Find the first comment by a user for an issue."""
    for comment in issue.get_comments():
        if comment.user.login == user:
            return comment


def process_pr(grepo, pr):
    """Initial processing of a PR including linking and labeling"""
    print(f"\nProcessing pr {pr.number}")

    # check if we've already seen this pr
    if user_comment(pr):
        print(f"Issue {pr.number} already processed. Skipping.")
        return

    # check if our bot opened this pr
    if pr.user.login == GITHUB_USER:
        return

    r_issues = []
    for commit in pr.get_commits():
        message = commit.commit.message
        r_issues.extend(pattern.findall(message))

    # UPDATE THE ISSUE IN REDMINE

    needs_cherry_pick = False

    if not r_issues:
        print(f"Issue {pr.number} has no attached redmine ticket.")
        comment = (
            "WARNING!!! This PR is not attached to an issue. In most cases this is not advisable. "
            "Please see [our PR docs](http://docs.pulpproject.org/contributing/git.html#commit-message)"
            " for more information about how to attach this PR to an issue."
        )
    else:
        print(f"Found redmine ticket(s) for issue {pr.number}.")
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

    return
    grepo.get_issue(pr.number).create_comment(comment)

    # ADD LABELS

    if needs_cherry_pick:
        print(f"Issue {pr.number} has attached bug. Adding cherry pick label.")
        try:
            label = grepo.get_label("Needs Cherry Pick")
        except UnknownObjectException:
            print("No cherry pick label found.")
            return

        labels = pr.labels + [label]
        grepo.get_issue(pr.number).edit(labels=[lbl.name for lbl in labels])


def merge_pr(pr):
    """Check if a PR is ready for merge and if so, attempt to merge it."""
    print(f"Checking PR {pr.number} to see if it's mergeable.")

    if pr.draft:
        print(f"PR {pr.number} is a draft, skipping merge.")
        return

    if pr.get_reviews().totalCount < 1:
        # technically not required if branch protection is set up properly since
        # mergeable_state will say "blocking" if there aren't enough reviews
        print(f"PR {pr.number} has not been reviewed, skipping merge.")
        return

    if pr.mergeable_state != "clean":
        print(f"PR {pr.number} has state {pr.mergeable_state}, skipping merge.")
        return

    if any(commit for commit in pr.get_commits() if
           commit.raw_data["commit"]["verification"]["verified"]):
        merge_method = "merge"
    else:
        merge_method = "rebase"

    pr.merge(merge_method=merge_method)
    print(f"Merged PR {pr.number} by {merge_method} method.\n")


def main():
    for repo in REPOS:
        print(f"\n\nProcessing repository {repo}.")
        grepo = g.get_repo(f"{ORG}/{repo}")
        issues = grepo.get_issues(since=SINCE)

        for issue in issues:
            pr = issue.as_pull_request()
            process_pr(grepo, pr)

            if repo in AUTO_MERGE_REPOS:
                merge_pr(pr)


if __name__ == "__main__":
    main()
