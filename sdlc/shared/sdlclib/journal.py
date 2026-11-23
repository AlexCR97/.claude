"""
A remote ticket's journal upstream: the comments `checkpoint` posted, one per entry.

The marker is defined in `journal.md`. A comment is read tolerantly of the
whitespace a source may add around it (a BOM, blank lines, CRLF), but its
first line must be the marker and nothing else: a comment that merely quotes
one is a human's, not an entry.
"""

import re
from pathlib import Path
from typing import NotRequired, TypedDict, TypeVar

MARKER = re.compile(r"sdlc-journal-entry `(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z\.md)`")


class Comment(TypedDict):
    text: str
    author: str | None


class Entry(TypedDict):
    name: str
    entry: str
    author: str | None


class Mirrored(TypedDict):
    written: list[str]
    kept: list[str]


class Comparison(TypedDict):
    upstream: list[str]
    unmirrored: list[str]
    newest_unmirrored: NotRequired[Entry]


Item = TypeVar("Item")


def parse(comment: Comment) -> Entry | None:
    text = (comment["text"] or "").replace("\r\n", "\n").lstrip("﻿ \t\n")
    first, _, rest = text.partition("\n")
    match = MARKER.fullmatch(first.strip())
    if not match:
        return None
    return Entry(
        name=match.group(1),
        entry=rest.lstrip("\n").rstrip() + "\n",
        author=comment["author"],
    )


def entries(comments: list[Comment]) -> list[Entry]:
    """Every entry upstream, oldest first; a name posted twice counts once, as first posted."""
    found: dict[str, Entry] = {}
    for comment in comments:
        entry = parse(comment)
        if entry:
            found.setdefault(entry["name"], entry)
    return [found[name] for name in sorted(found)]


def without_entries(items: list[Item], comments: list[Comment]) -> list[Item]:
    """The items whose comment is not a journal entry; `comments` holds each item's comment, in order."""
    return [
        item
        for item, comment in zip(items, comments, strict=True)
        if not parse(comment)
    ]


def mirror(comments: list[Comment], journal_dir: Path) -> Mirrored:
    written: list[str] = []
    kept: list[str] = []
    for entry in entries(comments):
        path = journal_dir / entry["name"]
        if path.exists():
            kept.append(entry["name"])
            continue
        journal_dir.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(entry["entry"])
        written.append(entry["name"])
    return {"written": written, "kept": kept}


def compare(comments: list[Comment], journal_dir: Path) -> Comparison:
    found = entries(comments)
    unmirrored = [
        entry for entry in found if not (journal_dir / entry["name"]).exists()
    ]
    report: Comparison = {
        "upstream": [entry["name"] for entry in found],
        "unmirrored": [entry["name"] for entry in unmirrored],
    }
    if unmirrored:
        report["newest_unmirrored"] = unmirrored[-1]
    return report
