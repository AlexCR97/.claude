#!/usr/bin/env python3
"""
A ticket's pull request record: `pulls.md`, one link per pull request that
delivers the ticket's work.

The same pull request can deliver several tickets, so a record is per ticket
and nothing here knows another ticket exists.
"""

import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

from . import azrest, proc, workspace
from .errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError
from .layout import Location

FILENAME = "pulls.md"

ENTRY = re.compile(r"^- \[([^\]]+)\]\((\S+?)\)(?: — (.*))?$")
STAMP_FORMAT = "%Y-%m-%d %H:%M UTC"
GITHUB_REVIEW = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "changes requested",
    "REVIEW_REQUIRED": "review required",
}

GITHUB_PULL = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$")
# Azure DevOps addresses a pull request under either organization form, as it does a work item.
ADO_PULL = re.compile(
    r"^https://(?:dev\.azure\.com/(?P<org>[^/]+)|(?P<legacy_org>[^/.]+)\.visualstudio\.com)"
    r"/(?P<project>[^/]+)/_git/(?P<repository>[^/]+)/pullrequest/(?P<number>\d+)/?$"
)
ADO_API_VERSION = "7.1"
ADO_STATE = {"active": "open", "completed": "merged", "abandoned": "closed"}


def path(location: Location) -> Path:
    return location.dir / FILENAME


def label(url: str) -> str:
    github = GITHUB_PULL.match(url)
    if github:
        owner, repository, number = github.groups()
        return f"{owner}/{repository}#{number}"
    ado = ADO_PULL.match(url)
    if not ado:
        raise TicketError(
            f"'{url}' is not a GitHub or Azure DevOps pull request address",
            EXIT_ERROR,
            "Use https://github.com/{owner}/{repository}/pull/{number} or "
            "https://dev.azure.com/{organization}/{project}/_git/{repository}/pullrequest/{id}.",
        )
    return f"{unquote(ado['project'])}/{ado['repository']}!{ado['number']}"


def add(location: Location, url: str) -> Path:
    entry = f"- [{label(url)}]({url})\n"
    record = path(location)
    existing = record.read_text(encoding="utf-8") if record.is_file() else ""
    if f"]({url})" in existing:
        return record
    record.write_text(existing + entry, encoding="utf-8", newline="\n")
    return record


@dataclass(frozen=True)
class PullRequest:
    label: str
    url: str
    # Empty until the first refresh.
    status: str = ""


def entries(location: Location) -> list[PullRequest]:
    record = path(location)
    if not record.is_file():
        return []
    found = (
        ENTRY.match(line) for line in record.read_text(encoding="utf-8").splitlines()
    )
    return [PullRequest(m[1], m[2], m[3] or "") for m in found if m]


def github_checks(rollup: list[dict]) -> str:
    """One word for a pull request's checks: failing wins over pending, pending over passing."""
    failed = {
        "FAILURE",
        "ERROR",
        "TIMED_OUT",
        "CANCELLED",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
    }
    if any((c.get("conclusion") or c.get("state")) in failed for c in rollup):
        return "failing"
    if any(
        c.get("status", "COMPLETED") != "COMPLETED" or c.get("state") == "PENDING"
        for c in rollup
    ):
        return "pending"
    return "passing" if rollup else ""


def github_status(url: str) -> str:
    code, stdout, stderr = proc.run(
        [
            "gh",
            "pr",
            "view",
            url,
            "--json",
            "state,isDraft,reviewDecision,statusCheckRollup",
        ]
    )
    if code != 0:
        detail = stderr.strip() or f"exit code {code}"
        raise TicketError(f"gh could not read {url}: {detail}")
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise TicketError(
            f"gh returned output for {url} that is not JSON: {exc}"
        ) from exc
    state = "draft" if data.get("isDraft") else data["state"].lower()
    parts = [state]
    checks = github_checks(data.get("statusCheckRollup") or [])
    if checks:
        parts.append(f"checks {checks}")
    review = GITHUB_REVIEW.get(data.get("reviewDecision") or "")
    if review:
        parts.append(review)
    return ", ".join(parts)


def discover(location: Location, patterns: list[str]) -> list[str]:
    """
    Record the pull requests whose head is a branch the plan's Workspace section lists.

    The Workspace section is what ties a branch to this ticket; a branch's name
    never does, so a pull request on a branch the plan does not list is not found.
    A protected branch is never the head of a ticket's pull request, and a fork's
    `main` would be matched to the wrong ticket, so those rows are skipped.
    """
    plan = location.dir / "plan.md"
    if not plan.is_file():
        raise TicketError(
            f"{location.qualified} has no plan.md",
            EXIT_NOT_FOUND,
            "Run /ticket-plan first.",
        )
    rows, _ = workspace.parse_rows(plan.read_text(encoding="utf-8").split("\n"))
    found: list[str] = []
    for row, state in zip(rows, workspace.inspect(rows, patterns)):
        if state["protected"] or state["missing"]:
            continue
        code, stdout, stderr = proc.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                row.branch,
                "--state",
                "all",
                "--json",
                "url",
            ],
            cwd=str(row.path),
        )
        if code != 0:
            raise TicketError(
                f"gh could not list pull requests of {row.branch}: {stderr.strip()}"
            )
        for pull in json.loads(stdout):
            add(location, pull["url"])
            found.append(pull["url"])
    return found


def ado_review(votes: list[int]) -> str:
    """
    A reviewer's vote is 10 approved, 5 approved with suggestions, -5 waiting for
    the author or -10 rejected; any negative vote outweighs an approval.
    """
    worst = min(votes, default=0)
    if worst <= -10:
        return "rejected"
    if worst < 0:
        return "waiting for author"
    return "approved" if any(vote >= 5 for vote in votes) else ""


def ado_status(url: str) -> str:
    ado = ADO_PULL.match(url)
    org = ado["org"] or ado["legacy_org"]
    api = (
        f"https://dev.azure.com/{org}/{ado['project']}/_apis/git/repositories/"
        f"{ado['repository']}/pullrequests/{ado['number']}"
    )
    try:
        data = azrest.get_json(api, api_version=ADO_API_VERSION)
    except azrest.AzRestError as exc:
        raise TicketError(f"Azure DevOps could not read {url}: {exc}") from exc
    status = data["status"]
    state = "draft" if data.get("isDraft") else ADO_STATE.get(status, status)
    review = ado_review(
        [reviewer.get("vote", 0) for reviewer in data.get("reviewers") or []]
    )
    return f"{state}, {review}" if review else state


def status_of(url: str) -> str:
    return github_status(url) if GITHUB_PULL.match(url) else ado_status(url)


def stamp_of(text: str) -> str:
    match = re.search(r"^Status as of (.+)\.$", text, re.MULTILINE)
    return match.group(1) if match else ""


def render(stamp: str, items: list[PullRequest], failure: str = "") -> str:
    lines = ["# Pull requests", ""]
    lines.append(
        f"Status as of {stamp}." if stamp else "Statuses have not been refreshed."
    )
    if failure:
        lines.append(f"Refresh failed: {failure}")
    lines.append("")
    lines += [
        f"- [{pr.label}]({pr.url}) — {pr.status}"
        if pr.status
        else f"- [{pr.label}]({pr.url})"
        for pr in items
    ]
    return "\n".join(lines) + "\n"


def refresh(location: Location) -> list[PullRequest]:
    """
    Rewrite every status from its host, or change nothing but a failure note.

    A refresh that fails halfway would leave one timestamp over statuses of two
    ages, so it is all or nothing: the old statuses and their time stay.
    """
    record = path(location)
    current = entries(location)
    if not current:
        return []
    previous = stamp_of(record.read_text(encoding="utf-8")) if record.is_file() else ""
    try:
        found = [replace(pr, status=status_of(pr.url)) for pr in current]
    except TicketError as exc:
        record.write_text(
            render(previous, current, exc.message), encoding="utf-8", newline="\n"
        )
        raise TicketError(
            f"Refresh failed: {exc.message}",
            EXIT_ERROR,
            "The previous statuses were kept.",
        ) from exc
    stamp = datetime.now(UTC).strftime(STAMP_FORMAT)
    record.write_text(render(stamp, found), encoding="utf-8", newline="\n")
    return found
