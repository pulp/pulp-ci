#!/bin/env python3

# Reference: https://jira.readthedocs.io

import typing as t
from pathlib import Path
import json
import tomllib
from collections import defaultdict
import dataclasses
from functools import cached_property
import os
import time

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


def read_config(conf_path: Path) -> Config:
    conf_path = Path(click.get_app_dir("pulp/pj")) / ".pj_config"
    data = tomllib.loads(conf_path.read_text())["default"]
    return Config(**data)


class JiraContext:
    def __init__(self) -> None:
        self._conf_path = Path(click.get_app_dir("pulp/pj")) / ".pj_config"
        self._config: Config = read_config(self._conf_path)
        self._cache_path = (
            Path(os.environ.get("XDG_CACHE_HOME") or "~/.cache") / "pulp" / ".pj_cache"
        )
        self._cache_dirty: bool = False
        self._cache: Cache = Cache()
        self.read_cache()

        self.project: str = self._config.project
        self.board: str = self._config.board

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
        if self._cache_path.exists():
            self._cache = Cache.model_validate_json(self._cache_path.read_text())
        else:
            self._cache = Cache()

    def dump_cache(self) -> None:
        if self._cache_dirty:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(self._cache.model_dump_json())

    def search_issues_paginated(
        self, jql: str, max_results: int | None = None
    ) -> t.Iterator[Issue]:
        start_at = 0
        per_page = 50 if max_results is None else min(50, max_results)
        while results := self.jira.search_issues(
            jql,
            maxResults=per_page,
            startAt=start_at,
        ):
            yield from results
            start_at += per_page
            if max_results is not None and start_at + per_page > max_results:
                per_page = max_results - start_at
                if per_page <= 0:
                    break

    def search_epic(self, epic_id: str) -> Issue:
        if epic_id.lower().startswith(self.project.lower()):
            epic = self.jira.issue(epic_id)
            assert epic.fields.issuetype.name == "Epic"
        else:
            epic = next(
                self.search_issues_paginated(
                    f"'Epic Name' = '{epic_id}'", max_results=1
                )
            )

        return epic

    def issue_type_emoji(self, issuetype: str) -> str:
        """
         🚫 ☣️

        Observation: 📡
        Investigation: 🔬
        Experiment: 🧪
        """
        if issuetype == "Feature":
            return "💶"
        elif issuetype == "Epic":
            return "🎭"
        elif issuetype == "Story":
            return "📰"
            # return "📖"
        elif issuetype == "Bug":
            return "🐞"
        elif issuetype == "Task":
            return "🔧"
        elif issuetype == "Sub-task":
            return "🥷"
        elif issuetype == "Outcome":
            return "🏁"
        elif issuetype == "Vulnerability":
            return "💣"
            return "🛟"
        elif issuetype == "Weakness":
            return "🦺"
            # return "🩸"
        else:
            return "❓"

    def priority_emoji(self, priority: str) -> str:
        """
        'Blocker'
        'Urgent'
        'Critical'
        'Must Have'
        'High'
        'Major'
        'Should Have'
        'Normal'
        'Medium'
        'Minor'
        'Low'
        'Could Have'
        'Trivial'
        'Optional'
        "Won't Have"
        'Undefined'
        'Unprioritized'
        """
        if priority == "Blocker":
            return "⛔"
        elif priority == "Critical":
            return "🌋"
        elif priority == "Major":
            return "➕"
        elif priority == "Normal":
            return "🟰"
        elif priority == "Minor":
            return "➖"
        elif priority == "Undefined":
            return "⭕"
        else:
            return "❓"
        return priority

    def status_emoji(self, status: str) -> str:
        if status == "New":
            return "✨"
        elif status == "Refinement":
            return "✂️"
        elif status == "In Progress":
            return "🧵"
        elif status == "Closed":
            return "🚪"
        else:
            return "❓"

    def resolution_emoji(self, resolution: str) -> str:
        if resolution == "Done":
            return "✅"
        elif resolution == "Won't Do":
            return "🚮"
        elif resolution == "Cannot Reproduce":
            return "☢️"
            # return "⁉️"
        elif resolution == "Can't Do":
            return "❓"
        elif resolution == "Duplicate":
            return "♊"
        elif resolution == "Not a Bug":
            return "❓"
        elif resolution == "Done-Errata":
            return "❓"
        elif resolution == "MirrorOrphan":
            return "❓"
        elif resolution == "Obsolete":
            return "❓"
        elif resolution == "Test Pending":
            return "❓"
        else:
            return "❓"

    def print_issue(self, issue: Issue) -> None:
        # TODO priority
        issuetype: str = self.issue_type_emoji(issue.fields.issuetype.name)
        issue_key: str = issue.key
        status: str = self.status_emoji(issue.fields.status.name)
        if issue.fields.resolution is not None:
            status += self.resolution_emoji(issue.fields.resolution.name)
        if str(issue.get_field(self.field_ids["Blocked"])) != "False":
            # Don't ask...
            status += "🚧"
        if issue.get_field(self.field_ids["Flagged"]):
            status += "🚩"

        priority: str = self.priority_emoji(issue.fields.priority.name)
        storypoints: float = issue.get_field(self.field_ids["Story Points"])
        sp: str = f"{storypoints:.1f}" if storypoints is not None else "N/A"
        summary: str = issue.fields.summary
        print(
            f"{issuetype:2.2}{issue_key:11.11}{status:4.4}{priority:2.2}{sp:>7.7} {issue.permalink()} {summary}"
        )

    def print_issue_detail(self, issue: Issue) -> None:
        print(issue.fields.issuetype.name, issue)
        if issue.fields.issuetype.name == "Epic":
            print(issue.get_field(self.field_ids["Epic Name"]))
        print(issue.permalink())
        print(issue.fields.summary)
        print(issue.fields.description)
        for fieldname in [
            "Status",
            "Blocked",
            "Flagged",
            "Assignee",
            "Reporter",
            "Priority",
            "Story Points",
            "Resolution",
            "Epic Link",
            "Sprint",
            "Component/s",
            "Labels",
        ]:
            value: t.Any = issue.get_field(self.field_ids[fieldname])
            if isinstance(value, list):
                value = [str(item) for item in value]
            print("  " + fieldname + ":", value)

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
    ctx.obj = JiraContext()

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
@click.option("--include-resolved", is_flag=True)
@click.option(
    "--all-projects",
    is_flag=True,
    help="Do not limit the search to the configured project.",
)
@click.option("--task", "issuetype", flag_value="Task")
@click.option("--bug", "issuetype", flag_value="Bug")
@click.option("--story", "issuetype", flag_value="Story")
@click.option("--vulnerability", "issuetype", flag_value="Vulnerability")
@click.option("--epic", "issuetype", flag_value="Epic")
@click.option(
    "--condition", "conditions", multiple=True, help="Extra conditions in jql."
)
@click.option("--max-results", type=int, help="Only show first results.")
@pass_jira_context
def issues(
    ctx: JiraContext,
    /,
    my: bool | None,
    blocker: bool,
    include_resolved: bool,
    all_projects: bool,
    issuetype: str | None,
    conditions: t.Iterable[str],
    max_results: int | None,
) -> None:
    _conditions = []
    if not all_projects:
        _conditions.append(f"project = {ctx.project}")
    if not include_resolved:
        _conditions.append("resolution = Unresolved")
    if my is True:
        _conditions.append("assignee = currentUser()")
    elif my is False:
        _conditions.append("assignee is EMPTY")
    # my == None -> all items

    if blocker:
        _conditions.append("priority = blocker")

    if issuetype is not None:
        _conditions.append(f"issuetype = {issuetype}")

    _conditions.extend(conditions)

    jql = " AND ".join(_conditions) + " ORDER BY priority DESC, updated DESC"
    for issue in ctx.search_issues_paginated(jql, max_results=max_results):
        ctx.print_issue(issue)


@main.command()
def my_next_issue() -> None:
    """
    Use special intelligent logic to spit out the next issue you should work on.
    """
    click.echo("Starting up JirAI...")
    time.sleep(5)
    click.echo("Just kidding!")
    time.sleep(2)
    click.echo("Who do you think I am?")


@main.command()
@click.argument("search_phrase")
@pass_jira_context
@click.option("--max-results", type=int, help="Only show first results.")
def search(
    ctx: JiraContext,
    /,
    search_phrase: str,
    max_results: int | None,
) -> None:
    jql = f"project = {ctx.project} AND resolution = Unresolved AND text ~ '{search_phrase}' ORDER BY updated DESC"
    for issue in ctx.search_issues_paginated(jql, max_results=max_results):
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
        if issue.fields.issuetype.name == "Epic":
            jql = f"'Epic Link' = {issue.key}"
            for sub_issue in ctx.search_issues_paginated(jql):
                ctx.print_issue(sub_issue)


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
@click.option("--in-epic", default=None)
@click.option("--story-points", default=None, type=float)
@click.argument("summary")
@click.argument("description")
@pass_jira_context
def create(
    ctx: JiraContext,
    /,
    issuetype: str,
    priority: str,
    assign: bool,
    in_epic: str | None,
    story_points: float | None,
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
    if in_epic is not None:
        fields[ctx.field_ids["Epic Link"]] = ctx.search_epic(in_epic).key
    if story_points is not None:
        fields[ctx.field_ids["Story Points"]] = story_points
    issue = ctx.jira.create_issue(fields)
    ctx.print_issue_detail(issue)


@main.command()
@click.option("--summary")
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
@click.option("--in-epic", default=None)
@click.option("--story-points", default=None, type=float)
@click.argument("issue_id")
@pass_jira_context
def amend(
    ctx: JiraContext,
    /,
    summary: str | None,
    issuetype: str | None,
    priority: str | None,
    assign: bool | None,
    in_epic: str | None,
    story_points: float | None,
    issue_id: str,
) -> None:
    """
    Change attributes of an issue.
    """
    issue = ctx.jira.issue(issue_id)
    ctx.print_issue(issue)
    fields: dict[str, t.Any] = {}
    if summary is not None:
        print("Updating Summary")
        fields["summary"] = summary
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
    if in_epic is not None:
        epic_key = ctx.search_epic(in_epic).key
        print("Epic:", issue.get_field(ctx.field_ids["Epic Link"]), "->", epic_key)
        fields[ctx.field_ids["Epic Link"]] = epic_key
    if story_points is not None:
        print(
            "Story Points:",
            issue.get_field(ctx.field_ids["Story Points"]),
            "->",
            story_points,
        )
        fields[ctx.field_ids["Story Points"]] = story_points

    click.confirm("Continue?", abort=True)
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

    click.confirm("Continue?", abort=True)
    print(fields)
    click.echo("This does not seem to be implemented")


@main.command()
@click.argument("issue_id")
@pass_jira_context
def assign(ctx: JiraContext, /, issue_id: str) -> None:
    """
    Assign an issue to me.
    """
    issue = ctx.jira.issue(issue_id)
    ctx.print_issue(issue)
    click.confirm("Continue?", abort=True)
    ctx.jira.assign_issue(issue, ctx.jira.current_user())


@main.command()
@click.argument("issue_id")
@pass_jira_context
def add_to_sprint(ctx: JiraContext, /, issue_id: str) -> None:
    issue = ctx.jira.issue(issue_id)
    board = ctx.jira.boards(name=ctx.board, projectKeyOrID=ctx.project)[0]
    sprint = ctx.jira.sprints(board.id, state=["active"])[0]
    ctx.print_issue(issue)
    click.confirm(f"Add to sprint '{sprint}'?", abort=True)
    ctx.jira.add_issues_to_sprint(sprint.id, [issue.key])


@main.command()
@click.argument("issue_id")
@pass_jira_context
def flag(
    ctx: JiraContext,
    /,
    issue_id: str,
):
    """
    Flag issue with impediment.

    NOT FUNCTIONAL
    """
    issue = ctx.jira.issue(issue_id)
    # TODO
    issue.update(
        fields={ctx.field_ids["Flagged"]: [{"set": [{"value": "Impediment"}]}]}
    )


@main.command()
@click.argument("issue_id")
@pass_jira_context
def unflag(
    ctx: JiraContext,
    /,
    issue_id: str,
):
    """
    Unflag issue from impediment.

    NOT FUNCTIONAL
    """
    issue = ctx.jira.issue(issue_id)
    # TODO
    issue.update(fields={ctx.field_ids["Flagged"]: [{"set": None}]})


@main.command()
@click.argument("issue_id")
@click.argument("story_points", type=float)
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
    ctx.print_issue(issue)
    print(
        "Story Points:",
        issue.get_field(ctx.field_ids["Story Points"]),
        "->",
        story_points,
    )
    click.confirm("Continue?", abort=True)
    issue.update(fields={ctx.field_ids["Story Points"]: story_points})


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
    ctx.print_issue(issue)
    click.confirm("Set to 'In Progress'?", abort=True)
    ctx.jira.transition_issue(issue, in_progress_id)


@main.command()
@click.option("--done", "resolution", flag_value="Done", default=True)
@click.option("--duplicate", "resolution", flag_value="Duplicate")
@click.option("--cannot-reproduce", "resolution", flag_value="Cannot Reproduce")
@click.argument("issue_id")
@pass_jira_context
def resolve_test(
    ctx: JiraContext,
    /,
    resolution: str,
    issue_id: str,
):
    """
    Close issue as done.
    (ATM this is the only supported resolution.)
    """
    issue = ctx.jira.issue(issue_id)
    resolution_id = next((res.id for res in ctx.resolutions if res.name == resolution))
    transitions = ctx.jira.transitions(issue)
    close_id = next((t["id"] for t in transitions if t["name"] == "Closed"))
    ctx.print_issue(issue)
    click.confirm(f"Close this as '{resolution}'?", abort=True)
    ctx.jira.transition_issue(issue, close_id, resolution={"id": resolution_id})


@main.group()
def debug() -> None:
    pass


@debug.command()
@pass_jira_context
def types(ctx: JiraContext, /) -> None:
    """
    Dump available issue types for the project.
    """
    for issue_type in ctx.issue_types:
        print(
            ctx.issue_type_emoji(issue_type.name),
            issue_type.name,
            f"(id={issue_type.id})",
        )


@debug.command()
@pass_jira_context
def resolutions(ctx: JiraContext, /) -> None:
    """
    Dump available resolutions.
    """
    for resolution in ctx.resolutions:
        print(resolution.name, f"(id={resolution.id})")


@debug.command()
@pass_jira_context
def fields(ctx: JiraContext, /) -> None:
    """
    Dump available fields.
    """
    for name, id in ctx.field_ids.items():
        print(name, "(id=" + id + ")")


@debug.command()
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
