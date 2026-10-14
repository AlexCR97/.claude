#!/usr/bin/env python3
"""
A ticket's journal: a directory holding one file per entry.

An entry is one session's account of itself and nothing can regenerate it, so
the journal is append-only by construction rather than by instruction: an entry
is only ever created, with an exclusive open, and never opened for writing
again. A resume then reads the newest file and nothing else.

Entries are named by their UTC timestamp, with `-` where a time would put a
`:` that Windows forbids, so a plain sort is a sort by time. Two entries in the
same second would collide; the later one moves to the next free second, which
keeps the sort correct where a suffix on the name would not.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError
from .layout import Location

DIRNAME = "journal"
LEGACY_FILENAME = "journal.md"

NAME_FORMAT = "%Y-%m-%dT%H-%M-%SZ"
NAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z\.md$")

# `## 2026-10-11 09:30 UTC — Phase 2, Step 2.3`: every entry opens with one.
HEADING_PATTERN = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?\s*(?:UTC|Z)?",
    re.MULTILINE,
)

ENTRY_SEPARATOR = re.compile(r"\n-{3,}\s*\Z")


def directory(location: Location) -> Path:
    return location.dir / DIRNAME


def entries(location: Location) -> list[Path]:
    """Every entry, oldest first. Anything in the directory that is not one is ignored."""
    return entries_in(location.dir)


def entries_in(ticket_dir: Path) -> list[Path]:
    root = ticket_dir / DIRNAME
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if NAME_PATTERN.match(path.name))


def latest(location: Location) -> Path | None:
    found = entries(location)
    return found[-1] if found else None


def timestamp_of(entry: Path) -> str:
    """The entry's UTC time as ISO-8601, read from its name."""
    stamp = datetime.strptime(entry.stem, NAME_FORMAT).replace(tzinfo=timezone.utc)
    return stamp.isoformat(timespec="seconds")


def parse_moment(text: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise TicketError(
            f"'{text}' is not a UTC timestamp", EXIT_ERROR, "Use YYYY-MM-DDTHH:MM:SS."
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def write(location: Location, text: str, at: datetime | None = None) -> Path:
    """Create a new entry. Never touches an existing file."""
    if not text.strip():
        raise TicketError("a journal entry cannot be empty", EXIT_ERROR)

    moment = (at or datetime.now(timezone.utc)).replace(microsecond=0)
    root = directory(location)
    root.mkdir(parents=True, exist_ok=True)

    while True:
        path = root / f"{moment.strftime(NAME_FORMAT)}.md"
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(text.rstrip() + "\n")
            return path
        except FileExistsError:
            moment += timedelta(seconds=1)


def split_legacy(text: str) -> list[tuple[datetime, str]]:
    """
    The entries of a single-file journal, oldest first, each with its own heading time.

    The file's title and ordering note precede the first heading and belong to
    no entry. An entry's trailing `---` is the file's separator, not its own.
    """
    matches = list(HEADING_PATTERN.finditer(text))
    found: list[tuple[datetime, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = ENTRY_SEPARATOR.sub("", text[match.start() : end].rstrip())
        day, hour, minute, second = match.groups()
        moment = datetime.fromisoformat(f"{day}T{hour}:{minute}:{second or '00'}")
        found.append((moment.replace(tzinfo=timezone.utc), body))
    # The file runs newest first; the stable sort keeps that order among equal times.
    found.reverse()
    found.sort(key=lambda entry: entry[0])
    return found


def migrate(location: Location) -> dict:
    """
    Split a ticket's `journal.md` into entry files and keep the original as a backup.

    Entries are written oldest first so that two sharing a minute keep their
    order when the later one is moved on a second.
    """
    legacy = location.dir / LEGACY_FILENAME
    if not legacy.is_file():
        raise TicketError(
            f"{location.qualified} has no {LEGACY_FILENAME} to migrate",
            EXIT_NOT_FOUND,
        )

    parsed = split_legacy(legacy.read_text(encoding="utf-8"))
    if not parsed:
        raise TicketError(
            f"no entry heading was found in {legacy}",
            EXIT_ERROR,
            "An entry opens with `## YYYY-MM-DD HH:MM UTC — {stage}`.",
        )

    created = [write(location, body, moment) for moment, body in parsed]

    backup = legacy.with_name(f"{LEGACY_FILENAME}.bak")
    counter = 1
    while backup.exists():
        counter += 1
        backup = legacy.with_name(f"{LEGACY_FILENAME}.bak.{counter}")
    legacy.rename(backup)

    return {
        "migrated": [path.name for path in created],
        "backup": str(backup),
    }
