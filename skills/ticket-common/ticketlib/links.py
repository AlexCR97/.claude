#!/usr/bin/env python3
"""
Relative markdown links, and what moving a ticket directory does to them.

A link between two tickets filed side by side survives any move that keeps
them together, because only the directories above them change. A link that
leaves the ticket for the workspace does not: its `../../..` counts levels of
the tickets home, so it breaks whenever that depth changes.

Nothing here rewrites a link. A move reports each one it breaks, with the
replacement that would repair it, because a journal entry is never edited and
the rest is someone's writing. The analysis is conservative in both
directions: a link that still resolves after the move is never reported, and
one that did not resolve before it is reported as already broken, never
"repaired" into pointing somewhere new.

One exception keeps a link's meaning rather than its current state: a target
outside the tickets home. That is the workspace, where a file can be missing
only because another branch is checked out, so the replacement keeps pointing
where the link always meant.
"""

import os
import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# The target of an inline markdown link or image, `[text](target)`.
LINK_PATTERN = re.compile(r"(\]\()([^)\s]+)(\))")

SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


@dataclass
class Relink:
    file: Path
    link: str
    status: str
    replacement: str | None = None
    target_missing: bool = False

    def as_dict(self) -> dict:
        entry = {"file": str(self.file), "link": self.link, "status": self.status}
        if self.replacement:
            entry["replacement"] = self.replacement
        if self.target_missing:
            entry["target_missing"] = True
        return entry


def relative_target(link: str) -> str | None:
    """The path part of a relative link, or None for a URL, an anchor or an absolute path."""
    # A drive letter reads as a one-letter scheme, so both are caught here.
    if not link or link.startswith(("#", "/", "\\")) or SCHEME_PATTERN.match(link):
        return None
    path = link.split("#", 1)[0].split("?", 1)[0]
    return urllib.parse.unquote(path) if path else None


def normalized(path: Path) -> Path:
    return Path(os.path.normpath(path))


def replacement_for(target: Path, new_file: Path, inside: Path) -> str:
    """
    A link from `new_file` to `target`: relative within the tickets home, absolute outside it.

    Outside the home is the workspace, whose position relative to a ticket is
    exactly what the move just changed — an absolute address is the only kind
    a later move cannot break.
    """
    try:
        target.relative_to(inside)
    except ValueError:
        return target.as_uri()
    try:
        relative = os.path.relpath(target, new_file.parent)
    except ValueError:
        return target.as_uri()
    return urllib.parse.quote(relative.replace(os.sep, "/"), safe="/._-~")


def analyze(
    text: str,
    old_file: Path,
    new_file: Path,
    to_new: Callable[[Path], Path],
    exists: Callable[[Path], bool],
    home: Path,
) -> list[Relink]:
    """
    Every relative link in `text` the move breaks, and what would repair each.

    `to_new` maps a path as it was before the move to where it is after;
    `exists` answers for a post-move path, so a dry run can ask it of paths
    that have not moved yet.
    """
    found: list[Relink] = []
    seen: set[str] = set()
    for match in LINK_PATTERN.finditer(text):
        link = match.group(2)
        relative = relative_target(link)
        # `rewrite` replaces every occurrence of a link at once, so one entry covers them all.
        if relative is None or link in seen:
            continue
        seen.add(link)

        if exists(normalized(new_file.parent / relative)):
            continue

        before = normalized(old_file.parent / relative)
        after = to_new(before)
        present = exists(after)
        if not present and is_inside(after, home):
            found.append(Relink(new_file, link, "already_broken"))
            continue

        fragment = link[len(link.split("#", 1)[0]) :]
        found.append(
            Relink(
                new_file,
                link,
                "broken_by_move",
                replacement_for(after, new_file, home) + fragment,
                target_missing=not present,
            )
        )
    return found


def is_inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def markdown_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.md") if path.is_file())


def in_snapshot(path: Path, ticket_dir: Path) -> bool:
    """
    Whether a file sits under `raw/`.

    A fetched attachment's links point wherever its author's repository put
    them, so a link there that was broken before a move says nothing about it.
    """
    return path.relative_to(ticket_dir).parts[0] == "raw"


def mentions(text: str, directory: Path) -> bool:
    """Whether text quotes a directory's absolute path, in either slash style."""
    lowered = text.casefold()
    native = str(directory).casefold()
    return native in lowered or native.replace("\\", "/") in lowered
