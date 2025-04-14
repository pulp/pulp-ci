#!/bin/env python3

# Reference: https://jira.readthedocs.io

import typing as t
from pathlib import Path
import json
import tomllib
from collections import defaultdict
import dataclasses

from jira import JIRA
from jira.resources import Issue, IssueType, Resolution
from jira.utils import remove_empty_attributes
from pydantic.dataclasses import dataclass
import click


@dataclass
class Config:
    server: str = "https://issues.redhat.com"
    token: str = ""
    project: str = "PULP"
    kanban_status: list[str] = dataclasses.field(
        default_factory=lambda: ["New", "In Progress", "Closed"]
    )


def read_config() -> Config:
    conf_path = Path(".") / ".jiraauth"
    data = tomllib.loads(conf_path.read_text())["default"]
    return Config(**data)


class JiraContext:
    def __init__(self, config: Config):
        self._config = config
        self._jira: JIRA | None = None
        self._fields: list[dict[str, t.Any]] | None = None
        self._sp_field_id: str | None = None
        self._issue_types: list[IssueType] | None = None
        self._resolutions: list[Resolution] | None = None
        self.project: str = config.project

    @property
    def jira(self) -> JIRA:
        if self._jira is None:
            self._jira = JIRA(server=self._config.server, token_auth=self._config.token)
        return self._jira

    @property
    def fields(self) -> list[dict[str, t.Any]]:
        if self._fields is None:
            # Idea: Cache them on disc.
            self._fields = self.jira.fields()
        return self._fields

    @property
    def sp_field_id(self) -> str:
        if self._sp_field_id is None:
            self._sp_field_id = next(
                (
                    field["id"]
                    for field in self.fields
                    if field["name"] == "Story Points"
                )
            )
        return self._sp_field_id

    @property
    def issue_types(self) -> list[IssueType]:
        if self._issue_types is None:
            self._issue_types = self.jira.issue_types_for_project(self.project)
        return self._issue_types

    @property
    def resolutions(self) -> list[Resolution]:
        if self._resolutions is None:
            self._resolutions = self.jira.resolutions()
        return self._resolutions

    def search_issues_paginated(
        self, jql: str, max_results: int | None = None
    ) -> t.Iterator[Issue]:
        start_at = 0
        max_results = 50  # TODO
        while results := self.jira.search_issues(
            jql,
            maxResults=max_results,
            startAt=start_at,
        ):
            yield from results
            start_at += max_results

    def print_issue(self, issue) -> None:
        print(
            issue.fields.issuetype.name,
            "\t",
            issue,
            "\t",
            issue.fields.status,
            "\t",
            issue.get_field(self.sp_field_id),
            "\t",
            issue.fields.summary,
        )

    def print_issue_detail(self, issue) -> None:
        print(issue.fields.issuetype.name, issue)
        print(issue.fields.summary)
        print(issue.fields.description)
        print("Status:", issue.fields.status.name)
        for fieldname in ["Story Points", "Resolution"]:
            field_id = next(
                (field["id"] for field in self.fields if field["name"] == fieldname)
            )
            print(fieldname + ":", issue.get_field(field_id))

    def print_kanban(self, issues) -> None:
        results: dict[str, list[Issue]] = defaultdict(list)
        sp_accumulator: dict[str, int] = defaultdict(int)
        for issue in issues:
            results[issue.fields.status.name].append(issue)
            sp_accumulator[issue.fields.status.name] += issue.get_field(
                self.sp_field_id
            )
        for status in self._config.kanban_status:
            issues = results[status]
            print(f"## {status} ({sp_accumulator[status]})")
            for issue in issues:
                self.print_issue(issue)


pass_jira_context = click.make_pass_decorator(JiraContext)


@click.group()
@click.pass_context
def main(ctx: click.Context, /) -> None:
    config = read_config()
    ctx.obj = JiraContext(config)


@main.command()
@click.option("--my/--unassigned", default=None, help="defaults to all")
@pass_jira_context
def sprint(ctx: JiraContext, /, my: bool | None) -> None:
    conditions = [
        f"project = {ctx.project}",
        "sprint in openSprints()",
    ]
    if my is True:
        conditions.append("assignee = currentUser()")
    elif my is False:
        conditions.append("assignee is EMPTY")
    # None -> all sprint items

    jql = " AND ".join(conditions) + " ORDER BY priority DESC, updated DESC"

    ctx.print_kanban(ctx.search_issues_paginated(jql))


@main.command()
@click.option("--my/--unassigned", default=None, help="defaults to all")
@click.option("--blocker", is_flag=True)
@pass_jira_context
def issues(ctx: JiraContext, /, my: bool | None, blocker: bool) -> None:
    conditions = [
        f"project = {ctx.project}",
        "status != 'Closed'",
    ]
    if my is True:
        conditions.append("assignee = currentUser()")
    elif my is False:
        conditions.append("assignee is EMPTY")
    # None -> all sprint items

    if blocker:
        conditions.append("priority = blocker")

    jql = " AND ".join(conditions) + " ORDER BY priority DESC, updated DESC"
    for issue in ctx.search_issues_paginated(jql):
        ctx.print_issue(issue)


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
    for issue in ctx.search_issues_paginated(jql):
        ctx.print_issue(issue)


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
        ctx.print_issue_detail(issue)


@main.command()
@click.option("--assign/--no-assign", default=False)
# @click.option("--task/--bug/--epic")
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
    ctx.print_issue_detail(issue)


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
    print("Story Points:", issue.get_field(ctx.sp_field_id), "->", story_points)
    issue.update(fields={ctx.sp_field_id: float(story_points)})


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
    resolution_id = next((res.id for res in ctx.resolutions if res.name == "Done"))
    transitions = ctx.jira.transitions(issue)
    close_id = next((t["id"] for t in transitions if t["name"] == "Closed"))
    ctx.jira.transition_issue(issue, close_id, resolution={"id": resolution_id})


@main.command()
@pass_jira_context
def types(ctx: JiraContext, /) -> None:
    """
    Dump available issue types for the project.
    """
    for issue_type in ctx.issue_types:
        print(issue_type.name, f"(id={issue_type.id})")


@main.command()
@pass_jira_context
def resolutions(ctx: JiraContext, /) -> None:
    """
    Dump available resolutions.
    """
    for resolution in ctx.resolutions:
        print(resolution.name, f"(id={resolution.id})")


@main.command()
@pass_jira_context
def fields(ctx: JiraContext, /) -> None:
    """
    Dump available fields.
    """
    for field in ctx.fields:
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
