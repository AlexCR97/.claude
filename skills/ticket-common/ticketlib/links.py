#!/usr/bin/env python3
"""
Relative markdown links, and what moving a ticket directory does to them.

A link between two tickets filed side by side survives any move that keeps
them together, because only the directories above them change. A link that
leaves the ticket for the workspace does not: its `../../..` counts levels of
the tickets home, so it breaks whenever that depth changes.

The rule every caller shares is conservative in both directions. A link that
still resolves after the move is never touched, and one that did not resolve
before it is never "fixed" into pointing somewhere new — it is reported as
already broken. Only a link the move itself broke is a candidate for rewriting,
and whether it is rewritten is the caller's decision: `journal.md` never is.

One exception keeps a link's meaning rather than its current state: a target
outside the tickets home. That is the workspace, where a file can be missing
only because another branch is checked out, and the address the link spelled
before the move is still exactly where it means. It is kept pointing there.
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


def rewrite(text: str, relinks: list[Relink]) -> str:
    replacements = {
        relink.link: relink.replacement
        for relink in relinks
        if relink.status == "broken_by_move" and relink.replacement
    }
    if not replacements:
        return text

    def swap(match: re.Match) -> str:
        link = match.group(2)
        return f"{match.group(1)}{replacements.get(link, link)}{match.group(3)}"

    return LINK_PATTERN.sub(swap, text)


def markdown_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.md") if path.is_file())


def in_snapshot(path: Path, ticket_dir: Path) -> bool:
    """
    Whether a file sits under `raw/`.

    A fetched attachment's links point wherever its author's repository put
    them, so a link there that was broken before a move says nothing about it.
    """
    return path.relative_to(ticket_dir).parts[0] == "raw"


def is_rewritable(path: Path, ticket_dir: Path) -> bool:
    """
    Whether a file's links may be repaired in place.

    Never `journal.md`, whose entries are never edited. Never anything under
    `raw/`, which is either a snapshot of the source or its hand-written body —
    the one a fetch would overwrite, the other a person's own words.
    """
    relative = path.relative_to(ticket_dir)
    return relative.parts[0] not in ("raw", "journal.md")


def mentions(text: str, directory: Path) -> bool:
    """Whether text quotes a directory's absolute path, in either slash style."""
    lowered = text.casefold()
    native = str(directory).casefold()
    return native in lowered or native.replace("\\", "/") in lowered
