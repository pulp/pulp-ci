# Reference: https://jira.readthedocs.io

import contextlib
import dataclasses
import json
import os
import time
import typing as t
from collections import defaultdict
from functools import cached_property
from pathlib import Path

import click
import tomllib
from jira import JIRA
from jira.resources import Issue, IssueType, Priority, Resolution, Status
from jira.utils import remove_empty_attributes
from pydantic import BaseModel
from pydantic.dataclasses import dataclass


@dataclass
class Config:
    email: str
    token: str
    server: str = "https://redhat.atlassian.net"
    project: str = "PULP"
    board: str = "Pulp Project Team Board"
    kanban_status: list[str] = dataclasses.field(
        default_factory=lambda: ["New", "In Progress", "Closed"]
    )


FIELD_IDS = {
    "Assignee": "assignee",
    "Status": "status",
    "Parent": "parent",
    "Parent Link": "customfield_10018",
    "Epic Link": "customfield_10014",
    "Epic Name": "customfield_10011",
    "Resolution": "resolution",
    "Priority": "priority",
    "Blocked": "customfield_10517",
    "Story Points": "customfield_10028",
    "Flagged": "customfield_10021",
    "Reporter": "reporter",
    "Sprint": "customfield_10020",
    "Component/s": "components",
    "Labels": "labels",
}

ISSUE_TYPE_EMOJIS = {
    "10142": "💶",  # Feature
    "10000": "🎭",  # Epic
    "10009": "📰",  # Story
    "10016": "🐞",  # Bug
    "10014": "🔧",  # Task
    "10015": "🥷",  # Sub-task
    "10130": "🏁",  # Outcome
    "10172": "💣",  # Vulnerability
    "10171": "🦺",  # Weakness
}

STATUS_EMOJIS = {
    "10142": "✨",  # "New"
    "10143": "✂️",  # "Refinement"
    "3": "🧵",  # "In Progress"
    "6": "🚪",  # "Closed"
}

PRIORITY_EMOJIS = {
    "10000": "⛔",  # Blocker
    "10001": "🌋",  # Critical
    "10002": "➕",  # Major
    "10003": "🟰",  # Normal
    "10004": "➖",  # Minor
    "10005": "⭕",  # Undefined
}

RESOLUTION_EMOJIS = {
    "10000": "✅",  # Done
    "10001": "🚮",  # Won't Do
    "10003": "☢️",  # Cannot Reproduce
    "10002": "♊",  # Duplicate
}


class Board(BaseModel):
    id: int
    name: str
    type: str


class Cache(BaseModel):
    field_ids: dict[str, str] | None = None
    issue_types: list[t.Any] | None = None
    resolutions: list[t.Any] | None = None
    board: Board | None = None


def read_config(conf_path: Path) -> Config:
    conf_path = Path(click.get_app_dir("pulp/pj")) / ".pj_config"
    data = tomllib.loads(conf_path.read_text())["default"]
    return Config(**data)


class JiraContext:
    def __init__(self, clear_cache: bool = False) -> None:
        self._conf_path = Path(click.get_app_dir("pulp/pj")) / ".pj_config"
        self._config: Config = read_config(self._conf_path)
        self._cache_path = (
            Path(os.environ.get("XDG_CACHE_HOME") or "~/.cache").expanduser() / "pulp" / ".pj_cache"
        )
        self._cache_dirty: bool = False
        self._cache: Cache = Cache()
        if clear_cache:
            with contextlib.suppress(FileNotFoundError):
                self._cache_path.unlink()
        else:
            self.read_cache()

        self.project: str = self._config.project

    @cached_property
    def jira(self) -> JIRA:
        return JIRA(
            server=self._config.server,
            basic_auth=(self._config.email, self._config.token),
        )

    @cached_property
    def field_ids(self) -> dict[str, str]:
        if self._cache.field_ids is None:
            self._cache.field_ids = {
                field.get("untranslatedName") or field["name"]: field["id"]
                for field in self.jira.fields()
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
            result = [IssueType({}, self.jira._session, raw=it) for it in self._cache.issue_types]
        return result

    @cached_property
    def resolutions(self) -> list[Resolution]:
        if self._cache.resolutions is None:
            result = self.jira.resolutions()
            self._cache.resolutions = [res.raw for res in result]
            self._cache_dirty = True
        else:
            result = [
                Resolution({}, self.jira._session, raw=res) for res in self._cache.resolutions
            ]
        return result

    @cached_property
    def board(self) -> Board:
        if self._cache.board is None:
            result = Board.model_validate(
                self.jira.boards(name=self._config.board, projectKeyOrID=self._config.project)[
                    0
                ].raw
            )
            self._cache.board = result
            self._cache_dirty = True
        else:
            result = self._cache.board
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
        per_page = 50
        next_page_token: str | None = None
        while True:
            if max_results is not None and per_page > max_results:
                per_page = max_results
            results = self.jira.enhanced_search_issues(
                jql, maxResults=per_page, nextPageToken=next_page_token
            )
            next_page_token = results.nextPageToken
            if max_results is not None:
                max_results -= len(results)
            yield from results
            if next_page_token is None or (max_results is not None and max_results <= 0):
                break

    def search_epic(self, epic_id: str) -> Issue:
        if epic_id.lower().startswith(self.project.lower() + "-"):
            epic = self.jira.issue(epic_id)
        else:
            epic = next(self.search_issues_paginated(f"'Epic Name' = '{epic_id}'", max_results=1))
        return epic

    def issue_type_emoji(self, issuetype: IssueType) -> str:
        return ISSUE_TYPE_EMOJIS.get(issuetype.id, "❓")

    def priority_emoji(self, priority: Priority) -> str:
        return PRIORITY_EMOJIS.get(priority.id, "❓")

    def status_emoji(self, status: Status) -> str:
        return STATUS_EMOJIS.get(status.id, "❓")

    def resolution_emoji(self, resolution: str) -> str:
        return RESOLUTION_EMOJIS.get(resolution.id, "❓")

    def print_issue(self, issue: Issue) -> None:
        # TODO priority
        issuetype: str = self.issue_type_emoji(issue.fields.issuetype)
        issue_key: str = issue.key
        status: str = self.status_emoji(issue.fields.status)
        if issue.fields.resolution is not None:
            status += self.resolution_emoji(issue.fields.resolution)
        if str(issue.get_field(FIELD_IDS["Blocked"])) != "False":
            # Don't ask...
            status += "🚧"
        if issue.get_field(FIELD_IDS["Flagged"]):
            status += "🚩"

        priority: str = self.priority_emoji(issue.fields.priority)
        storypoints: float = issue.get_field(FIELD_IDS["Story Points"])
        sp: str = f"{storypoints:.1f}" if storypoints is not None else "N/A"
        summary: str = issue.fields.summary
        print(
            f"{issuetype:2.2}{issue_key:11.11}{status:4.4}{priority:2.2}{sp:>7.7} {issue.permalink()} {summary}"
        )

    def print_issue_detail(self, issue: Issue) -> None:
        print(issue.fields.issuetype.name, issue)
        if issue.fields.issuetype.id == "10000":  # Epic
            print("Epic:", issue.get_field(FIELD_IDS["Epic Name"]))
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
            value: t.Any = issue.get_field(FIELD_IDS[fieldname])
            if isinstance(value, list):
                value = [str(item) for item in value]
            print("  " + fieldname + ":", value)

    def print_kanban(self, issues: t.Iterable[Issue]) -> None:
        results: dict[str, list[Issue]] = defaultdict(list)
        sp_accumulator: dict[str, float] = defaultdict(float)
        for issue in issues:
            results[issue.fields.status.name].append(issue)
            sp_accumulator[issue.fields.status.name] += (
                issue.get_field(FIELD_IDS["Story Points"]) or 0.0
            )
        for status, issues in results.items():
            print(f"## {status} ({sp_accumulator[status]})")
            for issue in issues:
                self.print_issue(issue)


pass_jira_context = click.make_pass_decorator(JiraContext)


@click.group()
@click.option("--clear-cache/--no-clear-cache", default=False)
@click.pass_context
def main(ctx: click.Context, /, clear_cache: bool) -> None:
    ctx.obj = JiraContext(clear_cache=clear_cache)

    ctx.call_on_close(ctx.obj.dump_cache)


@main.command()
@click.option("--future", "sprint_states", flag_value="future", multiple=True)
@click.option("--active", "sprint_states", flag_value="active", multiple=True)
@click.option("--closed", "sprint_states", flag_value="closed", multiple=True)
@click.option("--my/--unassigned", default=None, help="defaults to all")
@pass_jira_context
def sprints(ctx: JiraContext, /, sprint_states: list[str] | None, my: bool | None) -> None:
    filters = {}
    if sprint_states is not None:
        filters["state"] = ",".join(sprint_states)
    sprints = ctx.jira.sprints(ctx.board.id, **filters)

    for sprint in sprints:
        print(f"# {sprint.name}, [{sprint.state}]")


@main.command()
@click.option("--future", "sprint_state", flag_value="future")
@click.option("--active", "sprint_state", flag_value="active", default=True)
@click.option("--closed", "sprint_state", flag_value="closed")
@click.option("--my/--unassigned", default=None, help="defaults to all")
@pass_jira_context
def sprint(ctx: JiraContext, /, sprint_state: str, my: bool | None) -> None:
    for sprint in ctx.jira.sprints(ctx.board.id, state=[sprint_state]):
        conditions = [
            f"project = {ctx.project}",
            f"sprint = {sprint.id}",
        ]
        if my is True:
            conditions.append("assignee = currentUser()")
        elif my is False:
            conditions.append("assignee is EMPTY")
        # None -> all sprint items

        jql = " AND ".join(conditions) + " ORDER BY priority DESC, updated DESC"
        print(f"# {sprint.name}, [{sprint.state}]")
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
@click.option("--feature", "issuetype", flag_value="Feature")
@click.option("--outcome", "issuetype", flag_value="Outcome")
@click.option("--condition", "conditions", multiple=True, help="Extra conditions in jql.")
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
    click.echo("Starting up JirAI", nl=False)
    for i in range(5):
        time.sleep(1)
        click.echo(".", nl=False)
    click.echo("!")
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
                print(f"{comment.author.displayName} [{comment.created}]: {comment.body}")
        jql = f"'Parent Link' = {issue.key}"
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
@click.option("--parent", default=None)
@click.option("--story-points", default=None, type=float)
@click.option("--epic-name", default=None)
@click.argument("summary")
@click.argument("description")
@pass_jira_context
def create(
    ctx: JiraContext,
    /,
    issuetype: str,
    priority: str,
    assign: bool,
    parent: str | None,
    story_points: float | None,
    epic_name: str | None,
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
    if story_points is not None:
        fields[FIELD_IDS["Story Points"]] = story_points
    if issuetype == "Epic":
        if epic_name is None:
            raise click.UsageError("--epic-name is needed.")
        fields[FIELD_IDS["Epic Name"]] = epic_name
    if parent is not None:
        if issuetype == "Epic":
            link_name = "Parent Link"
        else:
            link_name = "Epic Link"
        fields[FIELD_IDS[link_name]] = ctx.search_epic(parent).key
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
@click.option("--parent", default=None)
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
    parent: str | None,
    story_points: float | None,
    issue_id: str,
) -> None:
    """
    Change attributes of an issue.
    """
    issue = ctx.jira.issue(issue_id)
    epic_link: str | None = None
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
    if parent is not None:
        parent_key = ctx.search_epic(parent).key
        if issuetype or issue.fields.issuetype == "Epic":
            link_name = "Parent Link"
            fields[FIELD_IDS[link_name]] = parent_key
        else:
            link_name = "Epic Link"
            epic_link = parent_key
        print(
            f"{link_name}: ",
            issue.get_field(FIELD_IDS[link_name]),
            "->",
            parent_key,
        )
    if story_points is not None:
        print(
            "Story Points:",
            issue.get_field(FIELD_IDS["Story Points"]),
            "->",
            story_points,
        )
        fields[FIELD_IDS["Story Points"]] = story_points

    click.confirm("Continue?", abort=True)
    if len(fields) > 0:
        issue.update(fields=fields)
    if epic_link:
        ctx.jira.add_issues_to_epic(epic_link, issue.key)


@main.command()
@click.argument("issue_id")
@click.argument("comment")
@pass_jira_context
def comment(ctx: JiraContext, /, issue_id: str, comment: str) -> None:
    """
    Comment on an issue.
    """
    issue = ctx.jira.issue(issue_id)
    ctx.print_issue(issue)
    click.confirm("Continue?", abort=True)
    ctx.jira.add_comment(issue, comment)


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

    for field_name in ["Story Points", "Priority"]:
        field_id = FIELD_IDS[field_name]
        orig_value = issue.get_field(field_id)
        value = click.prompt(field_name, default=orig_value)
        if value != orig_value:
            fields[field_id] = value

    # TODO "Components", "Labels"
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
@click.option("--future", "sprint_state", flag_value="future")
@click.option("--active", "sprint_state", flag_value="active", default=True)
@click.argument("issue_ids", nargs=-1, required=True)
@pass_jira_context
def add_to_sprint(ctx: JiraContext, /, issue_ids: tuple[str], sprint_state: str) -> None:
    issues = [ctx.jira.issue(issue_id) for issue_id in issue_ids]
    sprints = ctx.jira.sprints(ctx.board.id, state=[sprint_state])
    for issue in issues:
        ctx.print_issue(issue)
    if len(sprints) == 0:
        raise click.UsageError(f"There is no {sprint_state} sprint on this board.")
    elif len(sprints) == 1:
        sprint = sprints[0]
    else:
        for place, sprint in enumerate(sprints):
            click.echo(f"{place + 1:3}: {sprint} [{sprint.state}]")
        selection = click.prompt("Select a sprint", type=int) - 1
        if selection >= len(sprints) or selection < 0:
            raise click.Abort()
        sprint = sprints[selection - 1]
    click.confirm(f"Add to sprint '{sprint}' [{sprint.state}]?", abort=True)
    ctx.jira.add_issues_to_sprint(sprint.id, [issue.key for issue in issues])


@main.command()
@click.argument("issue_id")
@pass_jira_context
def flag(
    ctx: JiraContext,
    /,
    issue_id: str,
) -> None:
    """
    Flag issue with impediment.

    NOT FUNCTIONAL
    """
    issue = ctx.jira.issue(issue_id)
    # TODO
    issue.update(fields={FIELD_IDS["Flagged"]: [{"set": [{"value": "Impediment"}]}]})


@main.command()
@click.argument("issue_id")
@pass_jira_context
def unflag(
    ctx: JiraContext,
    /,
    issue_id: str,
) -> None:
    """
    Unflag issue from impediment.

    NOT FUNCTIONAL
    """
    issue = ctx.jira.issue(issue_id)
    # TODO
    issue.update(fields={FIELD_IDS["Flagged"]: [{"set": None}]})


@main.command()
@click.argument("issue_id")
@click.argument("story_points", type=float)
@pass_jira_context
def storypoint(
    ctx: JiraContext,
    /,
    issue_id: str,
    story_points: float,
) -> None:
    """
    Mark issue with a certain number of storypoints.
    """
    issue = ctx.jira.issue(issue_id)
    ctx.print_issue(issue)
    print(
        "Story Points:",
        issue.get_field(FIELD_IDS["Story Points"]),
        "->",
        story_points,
    )
    click.confirm("Continue?", abort=True)
    issue.update(fields={FIELD_IDS["Story Points"]: story_points})


@main.command()
@click.argument("issue_id")
@pass_jira_context
def in_progress(
    ctx: JiraContext,
    /,
    issue_id: str,
) -> None:
    """
    Transition issue to in progress.
    """
    issue = ctx.jira.issue(issue_id)
    transitions = ctx.jira.transitions(issue)
    transition = next((t for t in transitions if t["name"] == "In Progress"))
    # new_status = Status(ctx.jira.session, transition["to"])
    ctx.print_issue(issue)
    # click.confirm(f"Set to 'new_status.name' {ctx.status_emoji(new_status)}?", abort=True)
    click.confirm(f"Transition '{transition["name"]}'?", abort=True)
    ctx.jira.transition_issue(issue, transition["id"])


@main.command()
@click.option("--done", "resolution", flag_value="Done", default=True)
@click.option("--duplicate", "resolution", flag_value="Duplicate")
@click.option("--cannot-reproduce", "resolution", flag_value="Cannot Reproduce")
@click.option("--will-not-do", "resolution", flag_value="Won't Do")
@click.argument("issue_id")
@pass_jira_context
def resolve(
    ctx: JiraContext,
    /,
    resolution: str,
    issue_id: str,
) -> None:
    """
    Close issue with a resolution.
    """
    issue = ctx.jira.issue(issue_id)
    resolution_id = next((res.id for res in ctx.resolutions if res.name == resolution))
    transitions = ctx.jira.transitions(issue)
    close_id = next((t["id"] for t in transitions if t["name"] == "Closed"))
    ctx.print_issue(issue)
    click.confirm(f"Close this as '{resolution}'{ctx.resolution_emoji(resolution)}?", abort=True)
    ctx.jira.transition_issue(issue, close_id, resolution={"id": resolution_id})


@main.group()
def debug() -> None:
    pass


@debug.command()
@pass_jira_context
def fields(ctx: JiraContext, /) -> None:
    """
    Dump available fields.
    """
    for name, id in ctx.field_ids.items():
        print(name + " (id=" + id + ")")


@debug.command()
@pass_jira_context
def types(ctx: JiraContext, /) -> None:
    """
    Dump available issue types for the project.
    """
    for issue_type in ctx.issue_types:
        print(f"{ctx.issue_type_emoji(issue_type)} {issue_type.name} (id={issue_type.id})")


@debug.command()
@pass_jira_context
def resolutions(ctx: JiraContext, /) -> None:
    """
    Dump available resolutions.
    """
    for resolution in ctx.resolutions:
        print(f"{ctx.resolution_emoji(resolution)} {resolution.name} (id={resolution.id})")


@debug.command()
@pass_jira_context
def priorities(ctx: JiraContext, /) -> None:
    """
    Dump priorities.
    """
    for prio in ctx.jira.priorities():
        print(f"{ctx.priority_emoji(prio)} {prio.name} (id={prio.id})")


@debug.command()
@pass_jira_context
def status(ctx: JiraContext, /) -> None:
    """
    Dump status.
    """
    for status in ctx.jira.statuses():
        print(f"{ctx.status_emoji(status)} {status.name} (id={status.id})")


@debug.command()
@pass_jira_context
def shell(ctx: JiraContext, /) -> None:
    """
    Start an interactive ipython shell.

    The objects `jira` and `ctx` are preloaded.
    """
    import IPython

    IPython.start_ipython(argv=[], user_ns={"jira": ctx.jira, "ctx": ctx})
