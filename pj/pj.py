#!/bin/env python3

# Reference: https://jira.readthedocs.io

import typing as t
from pathlib import Path
import json
import tomllib

from jira import JIRA
from jira.utils import remove_empty_attributes
from pydantic.dataclasses import dataclass
import click


@dataclass
class Config:
    server: str = "https://issues.redhat.com"
    token: str = ""
    project: str = "PULP"


def read_config() -> Config:
    conf_path = Path(".") / ".jiraauth"
    data = tomllib.loads(conf_path.read_text())["default"]
    return Config(**data)


def search_issues_paginated(jira: JIRA, jql: str):
    start_at = 0
    max_results = 50
    while results := jira.search_issues(
        jql,
        maxResults=max_results,
        startAt=start_at,
    ):
        yield from results
        start_at += max_results


class JiraContext:
    def __init__(self, config: Config):
        self.jira: JIRA = JIRA(server=config.server, token_auth=config.token)
        self.project: str = config.project


pass_jira_context = click.make_pass_decorator(JiraContext)


@click.group()
@click.pass_context
def main(ctx: click.Context, /) -> None:
    config = read_config()
    ctx.obj = JiraContext(config)


@main.command()
@pass_jira_context
def issues(ctx: JiraContext, /) -> None:
    for issue in search_issues_paginated(
        ctx.jira,
        f"project = {ctx.project} AND resolution = Unresolved ORDER BY priority DESC, updated DESC",
    ):
        print(issue, issue.fields.summary)


@main.command()
@pass_jira_context
def blocker(ctx: JiraContext, /) -> None:
    for issue in ctx.jira.search_issues(
        f"project = {ctx.project} AND resolution = Unresolved AND priority = blocker ORDER BY updated DESC"
    ):
        print(issue, issue.fields.summary)


@main.command()
@pass_jira_context
def my_issues(ctx: JiraContext, /) -> None:
    jira = ctx.jira
    for issue in jira.search_issues(
        "assignee = currentUser() AND resolution = Unresolved order by updated DESC"
    ):
        print(issue, issue.fields.summary)


@main.command()
def my_next_issue() -> None:
    print("Who do you think I am?")


@main.command()
@click.argument("search_phrase")
@pass_jira_context
def search(
    ctx: JiraContext,
    /,
    search_phrase: str,
) -> None:
    jql = f"project = {ctx.project} AND resolution = Unresolved AND text ~ '{search_phrase}' ORDER BY updated DESC"
    for issue in ctx.jira.search_issues(jql):
        print(issue, issue.fields.summary)


@main.command()
@click.option("--raw", is_flag=True, default=False)
@click.argument("issue_id")
@pass_jira_context
def show(
    ctx: JiraContext,
    /,
    raw: bool,
    issue_id: str,
) -> None:
    issue = ctx.jira.issue(issue_id)
    if raw:
        raw_issue = issue.raw
        raw_issue["fields"] = remove_empty_attributes(raw_issue["fields"])
        raw_issue = remove_empty_attributes(raw_issue)
        print(json.dumps(raw_issue))
    else:
        print(issue.fields.issuetype.name, issue)
        print(issue.fields.summary)
        print(issue.fields.description)
        print("Status:", issue.fields.status.name)
        fields = ctx.jira.fields()
        for fieldname in ["Story Points", "Resolution"]:
            field_id = next(
                (field["id"] for field in fields if field["name"] == fieldname)
            )
            print(fieldname + ":", issue.get_field(field_id))


@main.command()
@click.option("--assign/--no-assign", default=True)
@click.argument("summary")
@click.argument("description")
@pass_jira_context
def create(
    ctx: JiraContext,
    /,
    assign: bool,
    summary: str,
    description: str,
) -> None:
    fields: dict[str, t.Any] = {
        "project": ctx.project,
        "issuetype": "Task",
        "summary": summary,
        "description": description,
    }
    if assign:
        fields["assignee"] = {"name": ctx.jira.current_user()}
    issue = ctx.jira.create_issue(fields)
    print(issue)


@main.command()
@click.argument("issue_id")
@click.argument("story_points")
@pass_jira_context
def storypoint(
    ctx: JiraContext,
    /,
    issue_id: str,
    story_points: float,
):
    """
    Mark issue with a certain number of storypoints.
    """
    issue = ctx.jira.issue(issue_id)
    sp_field_id = next(
        (field["id"] for field in ctx.jira.fields() if field["name"] == "Story Points")
    )
    print("Story Points:", issue.get_field(sp_field_id), "->", story_points)
    issue.update(fields={sp_field_id: float(story_points)})


@main.command()
@click.argument("issue_id")
@pass_jira_context
def close(
    ctx: JiraContext,
    /,
    issue_id: str,
):
    """
    Close issue as done.
    (ATM this is the only supported resolution.)
    """
    issue = ctx.jira.issue(issue_id)
    resolution_id = next(
        (res.id for res in ctx.jira.resolutions() if res.name == "Done")
    )
    transitions = ctx.jira.transitions(issue)
    close_id = next((t["id"] for t in transitions if t["name"] == "Closed"))
    ctx.jira.transition_issue(issue, close_id, resolution={"id": resolution_id})


@main.command()
@pass_jira_context
def types(ctx: JiraContext, /) -> None:
    """
    Dump available issue types for the project.
    """
    for issue_type in ctx.jira.issue_types_for_project(ctx.project):
        print(issue_type.name, f"(id={issue_type.id})")


@main.command()
@pass_jira_context
def resolutions(ctx: JiraContext, /) -> None:
    """
    Dump available resolutions.
    """
    for resolution in ctx.jira.resolutions():
        print(resolution.name, f"(id={resolution.id})")


@main.command()
@pass_jira_context
def fields(ctx: JiraContext, /) -> None:
    """
    Dump available fields.
    """
    for field in ctx.jira.fields():
        print(field["name"], "(id=" + field["id"] + ")")


@main.command()
@pass_jira_context
def shell(ctx: JiraContext, /) -> None:
    """
    Start an interactive ipython shell.

    The objects `jira` and `ctx` are preloaded.
    """
    import IPython

    IPython.start_ipython(argv=[], user_ns={"jira": ctx.jira, "ctx": ctx})


if __name__ == "__main__":
    main()
