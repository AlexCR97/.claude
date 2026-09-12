#!/usr/bin/env python3
"""
`ticket.json` — the sixth entry in a ticket root.

It is what lets every later skill agree on a ticket's identity, type and URL
without re-deriving them from source-shaped raw data. A driver reads
`ticket.json.url` and degrades to plain text when it is null; nothing else in
the suite needs to know whether the source has URLs at all.
"""

from datetime import datetime, timezone
from pathlib import Path

from . import config, paths

FILENAME = "ticket.json"

FIELDS = (
    "source",
    "id",
    "title",
    "type",
    "native_type",
    "state",
    "url",
    "last_fetched_at",
)


def path_for(source: str, ticket_id: str) -> Path:
    return paths.ticket_dir(source, ticket_id) / FILENAME


def load(source: str, ticket_id: str) -> dict:
    return config.read_json(path_for(source, ticket_id))


def save(source: str, ticket_id: str, data: dict) -> None:
    config.write_json(path_for(source, ticket_id), data)


def update(source: str, ticket_id: str, **changes) -> dict:
    """
    Merge changes into ticket.json, creating it when absent.

    A key passed as None is written as null rather than skipped. `url` is the
    reason: a source with no web address has to say so explicitly, because an
    absent key reads as "not fetched yet" while an explicit null reads as
    "this source has none" — and only the second is true.
    """
    record = load(source, ticket_id)
    record.setdefault("source", source)
    record.setdefault("id", ticket_id)
    record.update(changes)
    save(source, ticket_id, record)
    return record


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def on_disk(source: str, ticket_id: str) -> dict:
    """What of the ticket root actually exists, so a driver can stop early."""
    root = paths.ticket_dir(source, ticket_id)
    raw_dir = root / "raw"
    return {
        "ticket_dir": root.is_dir(),
        "ticket_json": (root / FILENAME).is_file(),
        "digest": (root / "digest.md").is_file(),
        "plan": (root / "plan.md").is_file(),
        "journal": (root / "journal.md").is_file(),
        "raw": raw_dir.is_dir() and any(raw_dir.iterdir()) if raw_dir.is_dir() else False,
        "artifacts": (root / "artifacts").is_dir(),
        "config": config.is_initialized(source),
    }


def list_all() -> list[dict]:
    """
    Every ticket on disk, across every source, newest first.

    This is what a driver prints when it has to ask which ticket the user
    means — the Source column is why it spans sources rather than one.
    """
    home = paths.tickets_home()
    if not home.is_dir():
        return []

    entries: list[dict] = []
    for source_path in sorted(home.iterdir()):
        if not source_path.is_dir():
            continue
        for ticket_path in sorted(source_path.iterdir()):
            if not ticket_path.is_dir():
                continue
            record = config.read_json(ticket_path / FILENAME)
            touched = newest_mtime(ticket_path)
            entries.append(
                {
                    "source": source_path.name,
                    "id": ticket_path.name,
                    "title": record.get("title"),
                    "type": record.get("type"),
                    "state": record.get("state"),
                    "url": record.get("url"),
                    "path": str(ticket_path),
                    "last_touched": touched,
                    "has_plan": (ticket_path / "plan.md").is_file(),
                    "has_journal": (ticket_path / "journal.md").is_file(),
                    "has_digest": (ticket_path / "digest.md").is_file(),
                }
            )

    entries.sort(key=lambda entry: entry["last_touched"] or "", reverse=True)
    return entries


def newest_mtime(directory: Path) -> str | None:
    newest = 0.0
    for candidate in ("journal.md", "plan.md", "digest.md", FILENAME):
        path = directory / candidate
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    if not newest:
        try:
            newest = directory.stat().st_mtime
        except OSError:
            return None
    return datetime.fromtimestamp(newest, tz=timezone.utc).isoformat(timespec="seconds")
