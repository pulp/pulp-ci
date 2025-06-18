#!/bin/env python3

# Reference: https://jira.readthedocs.io

import typing as t
from pathlib import Path
import json
import tomllib
from collections import defaultdict
import dataclasses
from functools import cached_property

from jira import JIRA
from jira.resources import Issue, IssueType, Resolution
from jira.utils import remove_empty_attributes
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
import click


@dataclass
class Config:
    server: str = "https://issues.redhat.com"
    token: str = ""
    project: str = "PULP"
    board: str = "Pulp Team Board"
    kanban_status: list[str] = dataclasses.field(
        default_factory=lambda: ["New", "In Progress", "Closed"]
    )


class Cache(BaseModel):
    field_ids: dict[str, str] | None = None
    issue_types: list[t.Any] | None = None
    resolutions: list[t.Any] | None = None


def read_config() -> Config:
    conf_path = Path(".") / ".pj_config"
    data = tomllib.loads(conf_path.read_text())["default"]
    return Config(**data)


class JiraContext:
    def __init__(self, config: Config):
        self._config: Config = config
        self._cache_dirty: bool = False
        self._cache: Cache = Cache()
        self.project: str = config.project
        self.board: str = config.board

    @cached_property
    def jira(self) -> JIRA:
        return JIRA(server=self._config.server, token_auth=self._config.token)

    @cached_property
    def field_ids(self) -> dict[str, str]:
        if self._cache.field_ids is None:
            self._cache.field_ids = {
                field["name"]: field["id"] for field in self.jira.fields()
            }
            self._cache_dirty = True
        return self._cache.field_ids

    @cached_property
    def issue_types(self) -> list[IssueType]:
        if self._cache.issue_types is None:
            result = self.jira.issue_types_for_project(self.project)
            self._cache.issue_types = [it.raw for it in result]
            self._cache_dirty = True
        else:
            result = [
                IssueType({}, self.jira._session, raw=it)
                for it in self._cache.issue_types
            ]
        return result

    @cached_property
    def resolutions(self) -> list[Resolution]:
        if self._cache.resolutions is None:
            result = self.jira.resolutions()
            self._cache.resolutions = [res.raw for res in result]
            self._cache_dirty = True
        else:
            result = [
                Resolution({}, self.jira._session, raw=res)
                for res in self._cache.resolutions
            ]
        return result

    def read_cache(self) -> None:
        cache_path = Path(".") / ".pj_cache"
        if cache_path.exists():
            self._cache = Cache.model_validate_json(cache_path.read_text())
        else:
            self._cache = Cache()

    def dump_cache(self) -> None:
        if self._cache_dirty:
            cache_path = Path(".") / ".pj_cache"
            cache_path.write_text(self._cache.model_dump_json())

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
        issue_type: str = issue.fields.issuetype.name
        issue_key: str = issue.key
        status: str = issue.fields.status.name
        storypoints: float = issue.get_field(self.field_ids["Story Points"])
        sp: str = f"{storypoints:.1f}" if storypoints is not None else "N/A"
        summary: str = issue.fields.summary
        print(f"{issue_type:7.7}{issue_key:11.11}{status:7.7}{sp:>7.7} {summary}")

    def print_issue_detail(self, issue) -> None:
        print(issue.fields.issuetype.name, issue)
        print(issue.fields.summary)
        print(issue.fields.description)
        print("Status:", issue.fields.status.name)
        print("Assignee:", issue.fields.assignee)
        print("Priority:", issue.fields.priority.name)
        for fieldname in ["Story Points", "Resolution", "Component/s", "Labels"]:
            print(fieldname + ":", issue.get_field(self.field_ids[fieldname]))

    def print_kanban(self, issues) -> None:
        results: dict[str, list[Issue]] = defaultdict(list)
        sp_accumulator: dict[str, float] = defaultdict(float)
        for issue in issues:
            results[issue.fields.status.name].append(issue)
            sp_accumulator[issue.fields.status.name] += (
                issue.get_field(self.field_ids["Story Points"]) or 0.0
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

    ctx.obj.read_cache()
    ctx.call_on_close(ctx.obj.dump_cache)


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
@click.option(
    "--condition", "conditions", multiple=True, help="Extra conditions in jql."
)
@pass_jira_context
def issues(
    ctx: JiraContext, /, my: bool | None, blocker: bool, conditions: t.Iterable[str]
) -> None:
    _conditions = [
        f"project = {ctx.project}",
        "status != 'Closed'",
    ]
    if my is True:
        _conditions.append("assignee = currentUser()")
    elif my is False:
        _conditions.append("assignee is EMPTY")
    # None -> all sprint items

    if blocker:
        _conditions.append("priority = blocker")

    _conditions.extend(conditions)

    jql = " AND ".join(_conditions) + " ORDER BY priority DESC, updated DESC"
    for issue in ctx.search_issues_paginated(jql):
        ctx.print_issue(issue)


@main.command()
def my_next_issue() -> None:
    """
    Use special intelligent logic to spit out the next issue you should work on.
    """
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
@click.option("--comments", is_flag=True, default=False)
@click.argument("issue_id")
@pass_jira_context
def show(
    ctx: JiraContext,
    /,
    raw: bool,
    comments: bool,
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
        if comments:
            print("Comments:")
            for comment in issue.fields.comment.comments:
                print(f"{comment.author.name} [{comment.created}]: {comment.body}")


@main.command()
@click.option("--task", "issuetype", flag_value="Task", default=True)
@click.option("--bug", "issuetype", flag_value="Bug")
@click.option("--story", "issuetype", flag_value="Story")
@click.option("--vulnerability", "issuetype", flag_value="Vulnerability")
@click.option("--epic", "issuetype", flag_value="Epic")
@click.option(
    "--priority",
    type=click.Choice(["Undefined", "Minor", "Normal", "Major", "Critical", "Blocker"]),
)
@click.option("--assign/--no-assign", default=False, help="Assign this issue to me.")
@click.argument("summary")
@click.argument("description")
@pass_jira_context
def create(
    ctx: JiraContext,
    /,
    issuetype: str,
    priority: str,
    assign: bool,
    summary: str,
    description: str,
) -> None:
    fields: dict[str, t.Any] = {
        "project": ctx.project,
        "issuetype": issuetype,
        "summary": summary,
        "description": description,
    }
    if priority is not None:
        fields["priority"] = {"name": priority}
    if assign:
        fields["assignee"] = {"name": ctx.jira.current_user()}
    issue = ctx.jira.create_issue(fields)
    ctx.print_issue_detail(issue)


@main.command()
@click.option("--task", "issuetype", flag_value="Task")
@click.option("--bug", "issuetype", flag_value="Bug")
@click.option("--story", "issuetype", flag_value="Story")
@click.option("--vulnerability", "issuetype", flag_value="Vulnerability")
@click.option("--epic", "issuetype", flag_value="Epic")
@click.option(
    "--priority",
    type=click.Choice(["Undefined", "Minor", "Normal", "Major", "Critical", "Blocker"]),
)
@click.option("--assign/--no-assign", default=None, help="Assign this issue to me.")
@click.argument("issue_id")
@pass_jira_context
def amend(
    ctx: JiraContext,
    /,
    issuetype: str,
    priority: str,
    assign: bool,
    issue_id: str,
) -> None:
    """
    Change attributes of an issue.
    """
    issue = ctx.jira.issue(issue_id)
    fields: dict[str, t.Any] = {}
    if issuetype is not None:
        print("Type:", issue.fields.issuetype, "->", issuetype)
        fields["issuetype"] = {"name": issuetype}
    if priority is not None:
        print("Priority:", issue.fields.priority, "->", priority)
        fields["priority"] = {"name": priority}
    if assign is True:
        print("Assignee:", issue.fields.assignee, "->", ctx.jira.current_user())
        fields["assignee"] = {"name": ctx.jira.current_user()}
    elif assign is False:
        print("Assignee:", issue.fields.assignee, "->", "N/A")
        fields["assignee"] = None

    issue.update(fields=fields)


@main.command()
@click.argument("issue_id")
@pass_jira_context
def groom(
    ctx: JiraContext,
    /,
    issue_id: str,
) -> None:
    """
    Interactively groom an issue for sprint readiness.
    """

    issue = ctx.jira.issue(issue_id)
    fields: dict[str, t.Any] = {}
    ctx.print_issue(issue)

    for field_name in ["Story Points", "Priority", "Components", "Labels"]:
        field_id = ctx.field_ids[field_name]
        orig_value = issue.get_field(field_id)
        value = click.prompt(field_name, default=orig_value)
        if value != orig_value:
            fields[field_id] = value

    print(fields)


@main.command()
@click.argument("issue_id")
@pass_jira_context
def assign(ctx: JiraContext, /, issue_id: str) -> None:
    """
    Assign an issue to me.
    """
    issue = ctx.jira.issue(issue_id)
    ctx.jira.assign_issue(issue, ctx.jira.current_user())


@main.command()
@click.argument("issue_id")
@pass_jira_context
def add_to_sprint(ctx: JiraContext, /, issue_id: str) -> None:
    issue = ctx.jira.issue(issue_id)
    board = ctx.jira.boards(name=ctx.board, projectKeyOrID=ctx.project)[0]
    sprint = ctx.jira.sprints(board.id, state=["active"])[0]
    ctx.jira.add_issues_to_sprint(sprint.id, [issue.key])


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
    print(
        "Story Points:",
        issue.get_field(ctx.field_ids["Story Points"]),
        "->",
        story_points,
    )
    issue.update(fields={ctx.field_ids["Story Points"]: float(story_points)})


@main.command()
@click.argument("issue_id")
@pass_jira_context
def in_progress(
    ctx: JiraContext,
    /,
    issue_id: str,
):
    """
    Transition issue to in progress.
    """
    issue = ctx.jira.issue(issue_id)
    transitions = ctx.jira.transitions(issue)
    in_progress_id = next((t["id"] for t in transitions if t["name"] == "In Progress"))
    ctx.jira.transition_issue(issue, in_progress_id)


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
    for name, id in ctx.field_ids.items():
        print(name, "(id=" + id + ")")


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
