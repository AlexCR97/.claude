"""
`sync`: bring a ticket's mirror and its pull request record up to date, in one
call every skill makes at its start.

The mirror is refreshed only when `fetch --check` finds something besides this
machine's own journal posts, so the call is cheap on an unchanged ticket.
Every pull request is read before anything is written, and a failure leaves
the mirror and `pulls.md` as they were, with the record saying the refresh failed.
"""

from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import TypedDict

from . import config as configuration
from . import fetch, guard, layout, providers, pulls, resolve
from .errors import SdlcError

# `journal_only` is left out: it is this machine's own posts, already in `journal/`.
STALE = frozenset({"journal_unmirrored", "changed", "never_mirrored", "stale_mirror"})


class Upstream(TypedDict):
    status: str
    refreshed: bool
    fields: list[str]
    journal: list[str]


class Skipped(TypedDict):
    path: str
    branch: str
    reason: str


class Pulls(TypedDict):
    changed: bool
    lines: list[pulls.Line]
    skipped: list[Skipped]


class SyncReport(TypedDict):
    ref: str
    ticket_dir: str
    changed: bool
    upstream: Upstream
    pulls: Pulls


@cache
def hosts() -> list[ModuleType]:
    """The providers of a host that holds pull requests, such as GitHub."""
    loaded = [
        providers.load_fetcher(source)
        for source in providers.list_sources()
        if providers.load_manifest(source)["capabilities"]["fetch"]
    ]
    return [module for module in loaded if hasattr(module, "pulls_headed_by")]


def require_pull_urls(urls: list[str]) -> None:
    for url in urls:
        if not any(host.PULL_URL.fullmatch(url.strip()) for host in hosts()):
            raise SdlcError(
                f"'{url}' is not the URL of a pull request on GitHub or Azure Repos"
            )


def locate(
    directory: Path, branch: str, product: layout.Product
) -> tuple[ModuleType, object] | str:
    """The host of the worktree's pull requests and where on it they live, or why there is none."""
    if not directory.is_dir():
        return "the directory is not on this machine"
    if guard.git(directory, "rev-parse", "--git-dir")[0] != 0:
        return "the directory is not in a git repository"
    if guard.protected_branches(str(directory), branch, product.ref)["protected"]:
        return "a protected branch heads no pull request of a ticket"
    code, remote = guard.git(directory, "remote", "get-url", "origin")
    if code != 0:
        return "it has no origin"
    for host in hosts():
        place = host.pull_host(remote)
        if place:
            return host, place
    return "its origin is not on GitHub or Azure Repos"


def found_in_workspace(
    ticket: layout.TicketDirectory,
) -> tuple[list[pulls.Line], list[Skipped]]:
    """The pull requests whose head is a branch the plan's Workspace lists."""
    found: list[pulls.Line] = []
    skipped: list[Skipped] = []
    for directory, branch in pulls.workspace_branches(ticket.dir / "plan.md"):
        located = locate(directory, branch, ticket.product)
        if isinstance(located, str):
            skipped.append(
                {"path": str(directory), "branch": branch, "reason": located}
            )
            continue
        host, place = located
        found += host.pulls_headed_by(place, branch)
    return found, skipped


def refresh_pulls(
    ticket: layout.TicketDirectory, named: list[str]
) -> tuple[list[pulls.Line], list[pulls.Line], list[Skipped]]:
    """The record's lines before and after, every status read anew; nothing is written."""
    before = pulls.read(ticket.dir / "pulls.md")
    found, skipped = found_in_workspace(ticket)
    by_url = {line["url"]: line for line in found}
    after: list[pulls.Line] = []
    for url in dict.fromkeys([line["url"] for line in before] + named + list(by_url)):
        line = by_url.get(url) or next(
            (read for host in hosts() if (read := host.pull_at(url))), None
        )
        # A line whose URL no host recognises was written by hand: it stays as it is.
        after.append(line or next(old for old in before if old["url"] == url))
    return before, after, skipped


def refresh_mirror(
    checked: fetch.CheckReport,
    reference_text: str,
    coordinate_arguments: list[str],
    context_text: str | None,
    cwd: Path,
) -> Upstream:
    upstream: Upstream = {
        "status": checked["status"],
        "refreshed": False,
        "fields": [],
        "journal": [],
    }
    if checked["status"] not in STALE:
        return upstream
    mirror = Path(checked["ticket_dir"]) / "raw" / "raw.json"
    before = fetch.read_mirror(mirror) if mirror.is_file() else None
    fetched = fetch.fetch(reference_text, coordinate_arguments, context_text, cwd)
    upstream["refreshed"] = True
    upstream["journal"] = fetched["fetched"]["journal"]["written"]
    if before is not None:
        fields_of = providers.load_fetcher(fetched["source"]).fields
        old, new = fields_of(before), fields_of(fetch.read_mirror(mirror))
        upstream["fields"] = [
            name for name in {**new, **old} if old.get(name) != new.get(name)
        ]
    return upstream


def sync(
    reference_text: str,
    pull_urls: list[str],
    coordinate_arguments: list[str],
    context_text: str | None,
    cwd: Path,
) -> SyncReport:
    require_pull_urls(pull_urls)
    ticket = resolve.locate_existing(
        configuration.load(),
        resolve.parse_reference(reference_text),
        coordinate_arguments,
        layout.parse_context(context_text),
        cwd,
    ).ticket
    record = ticket.dir / "pulls.md"
    try:
        checked = fetch.check(reference_text, coordinate_arguments, context_text, cwd)
        before, after, skipped = refresh_pulls(ticket, pull_urls)
        upstream = refresh_mirror(
            checked, reference_text, coordinate_arguments, context_text, cwd
        )
    except SdlcError as error:
        pulls.mark_failed(record, error.message)
        raise
    pulls.write(record, after, datetime.now(UTC))
    pulls_changed = before != after
    return {
        "ref": checked["ref"],
        "ticket_dir": checked["ticket_dir"],
        "changed": upstream["refreshed"] or pulls_changed,
        "upstream": upstream,
        "pulls": {"changed": pulls_changed, "lines": after, "skipped": skipped},
    }
