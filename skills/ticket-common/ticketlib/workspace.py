#!/usr/bin/env python3
"""
The Workspace section of a plan, and keeping it true when a worktree is swapped.

`ticket-implement` works only on a ticket branch. When the plan's workspace
holds a worktree with a protected branch checked out, that row is replaced by
a ticket worktree cut from the up-to-date default branch, and every reference
to the old one is rewritten in the same pass. A plan that still names the old
worktree after the swap would send the next session to the wrong code.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import guard, worktrees
from .errors import EXIT_ERROR, TicketError

NL = chr(10)
HEADING = "### Worktrees"
REWRITTEN_SUFFIXES = (".md", ".json", ".txt")


@dataclass
class Row:
    line: int
    repository: str
    branch: str
    kind: str
    path: Path


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_rows(lines: list[str]) -> tuple[list[Row], int]:
    """The worktree rows of the plan, and the index of the line just past their table."""
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == HEADING)
    except StopIteration as exc:
        raise TicketError(
            "plan.md has no Worktrees section", EXIT_ERROR, "Run /ticket-plan first."
        ) from exc

    first = start + 1
    while first < len(lines) and not lines[first].lstrip().startswith("|"):
        if lines[first].startswith("#"):
            raise TicketError("the Worktrees section has no table", EXIT_ERROR)
        first += 1

    end = first
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1

    rows: list[Row] = []
    # The first two lines are the header and its separator.
    for index in range(first + 2, end):
        values = cells(lines[index])
        if len(values) >= 4:
            rows.append(
                Row(index, values[0], values[1].strip("`"), values[2], Path(values[3].strip("`")))
            )
    return rows, end


def inspect(rows: list[Row], patterns: list[str]) -> list[dict]:
    """Each row's repository and whether the branch checked out in it is protected."""
    report = []
    for row in rows:
        entry = {
            "repository": row.repository,
            "branch": row.branch,
            "path": str(row.path),
            "protected": False,
            "missing": not row.path.is_dir(),
        }
        if not entry["missing"]:
            root = worktrees.repository_root(row.path)
            default = guard.default_branch(root)
            entry["repository_root"] = str(root)
            entry["protected"] = guard.is_protected(row.branch, default, patterns)
            if entry["protected"]:
                entry["reason"] = (
                    f"'{row.branch}' is a protected branch, so nothing may be edited in {row.path}"
                )
        report.append(entry)
    return report


def rewrite_references(
    ticket_dir: Path, plan_text: str, old_label: str, new_label: str, old_path: str, new_path: str
) -> tuple[str, list[str]]:
    """
    Replace the old worktree's label and path in the plan and under artifacts/.

    A label is `{repository}@{branch}`, the form a Target names a worktree by
    where the workspace holds more than one of a repository.
    """
    touched: list[str] = []

    # The new worktree usually sits inside the old one's repository, so the old
    # path is a prefix of the new one and of every sibling ticket worktree.
    old_path_pattern = re.compile(re.escape(old_path) + r"(?![\w.\-]|[\/]\.worktrees)")

    def swap(text: str) -> str:
        return old_path_pattern.sub(lambda _: new_path, text.replace(old_label, new_label))

    plan_text = swap(plan_text)
    artifacts = ticket_dir / "artifacts"
    if artifacts.is_dir():
        for path in sorted(artifacts.rglob("*")):
            if not path.is_file() or path.suffix not in REWRITTEN_SUFFIXES:
                continue
            try:
                original = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            updated = swap(original)
            if updated != original:
                path.write_text(updated, encoding="utf-8")
                touched.append(str(path))
    return plan_text, touched


def note_for(old: Row, new_branch: str, default: str) -> str:
    return (
        f"> **{old.repository}:** `{old.branch}` is a protected branch, so the work happens in "
        f"`{new_branch}`, a ticket worktree cut from `origin/{default}`."
    )


def swap_protected(
    ticket_dir: Path,
    patterns: list[str],
    branch: str,
    root_override: str | None,
    only_repositories: set[Path] | None,
    add_ignore: bool,
) -> dict:
    plan_path = ticket_dir / "plan.md"
    lines = plan_path.read_text(encoding="utf-8").split("\n")
    rows, _ = parse_rows(lines)
    inspected = inspect(rows, patterns)

    targets: dict[Path, tuple[Row, dict]] = {}
    for row, entry in zip(rows, inspected):
        if not entry["protected"]:
            continue
        root = Path(entry["repository_root"])
        if only_repositories is not None and root not in only_repositories:
            continue
        targets.setdefault(root, (row, entry))

    plans = {
        root: worktrees.propose(root, branch, patterns, root_override)
        for root in targets
    }
    for plan in plans.values():
        if plan.refusal:
            raise TicketError(plan.refusal, EXIT_ERROR)

    created = {root: worktrees.create(plan, add_ignore) for root, plan in plans.items()}

    text = "\n".join(lines)
    notes: list[str] = []
    touched: list[str] = []
    replaced: list[dict] = []
    for root, (row, _) in targets.items():
        result = created[root]
        old_label = f"{row.repository}@{row.branch}"
        new_label = f"{row.repository}@{result['branch']}"
        old_path = str(row.path)
        new_path = result["worktree"]
        text, files = rewrite_references(
            ticket_dir, NL.join(lines), old_label, new_label, old_path, new_path
        )
        lines = text.split(NL)
        lines[row.line] = (
            f"| {row.repository} | {result['branch']} | linked | `{new_path}` |"
        )
        touched.extend(files)
        notes.append(note_for(row, result["branch"], result["default_branch"]))
        replaced.append(
            {
                "repository": row.repository,
                "old_branch": row.branch,
                "old_path": old_path,
                "new_branch": result["branch"],
                "new_path": new_path,
                "created": result["created"],
            }
        )

    _, end = parse_rows(lines)
    lines[end:end] = ["", *notes]
    plan_path.write_text(NL.join(lines), encoding="utf-8")

    return {"replaced": replaced, "artifacts_rewritten": touched, "notes": notes}
