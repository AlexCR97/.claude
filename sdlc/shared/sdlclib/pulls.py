"""
The pull request record (`pulls.md`) and the branches its pull requests are
found from. The record's format is defined in `journal.md`.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from . import layout

NONE_YET = "No pull requests deliver this ticket yet."
LINE = re.compile(r"^- \[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)\) - (?P<status>.+)$")
FAILED = "Refresh failed:"


class Line(TypedDict):
    label: str
    url: str
    status: str


def read(path: Path) -> list[Line]:
    """The record's lines, in order; a record that does not exist has none."""
    if not path.is_file():
        return []
    return [
        Line(label=match["label"], url=match["url"], status=match["status"].strip())
        for match in map(LINE.match, path.read_text(encoding="utf-8").splitlines())
        if match
    ]


def write(path: Path, lines: list[Line], at: datetime) -> None:
    """Replaces the record with `lines` as of `at`, which clears a failed refresh."""
    listed = (
        "\n".join(
            f"- [{line['label']}]({line['url']}) - {line['status']}" for line in lines
        )
        if lines
        else NONE_YET
    )
    text = f"# Pull requests\n\nStatus as of {at:%Y-%m-%d %H:%M} UTC.\n\n{listed}\n"
    layout.replace_file(path, text.encode("utf-8"))


def mark_failed(path: Path, reason: str) -> None:
    """Keeps every status and the time as they were; a record that does not exist stays absent."""
    if not path.is_file():
        return
    kept = [
        line
        for line in path.read_text(encoding="utf-8").rstrip("\n").split("\n")
        if not line.startswith(FAILED)
    ]
    while kept and not kept[-1].strip():
        kept.pop()
    text = "\n".join(kept) + f"\n\n{FAILED} {reason.rstrip('.')}.\n"
    layout.replace_file(path, text.encode("utf-8"))


TABLE_ROW = re.compile(r"^\s*\|(.*)\|\s*$")


def workspace_branches(plan: Path) -> list[tuple[Path, str]]:
    """Each worktree the plan's Workspace lists, as (directory, branch), from its Worktrees table."""
    if not plan.is_file():
        return []
    section = re.search(
        r"^### Worktrees\s*$(.*?)(?=^#{1,3} |\Z)",
        plan.read_text(encoding="utf-8"),
        re.MULTILINE | re.DOTALL,
    )
    if not section:
        return []
    rows = [
        [cell.strip().strip("`").strip() for cell in match.group(1).split("|")]
        for match in map(TABLE_ROW.match, section.group(1).splitlines())
        if match
    ]
    if not rows:
        return []
    header = [cell.casefold() for cell in rows[0]]
    if "branch" not in header or "path" not in header:
        return []
    branch, path = header.index("branch"), header.index("path")
    return [
        (Path(row[path]), row[branch])
        for row in rows[1:]
        if len(row) == len(header)
        and row[branch]
        and row[path]
        and not set(row[branch]) <= set("-: ")
    ]
