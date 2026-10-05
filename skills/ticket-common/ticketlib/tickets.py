#!/usr/bin/env python3
"""
`ticket.json` — the sixth entry in a ticket directory.

It is what lets every later skill agree on a ticket's identity, type and URL
without re-deriving them from source-shaped raw data. A driver reads
`ticket.json.url` and degrades to plain text when it is null; nothing else in
the suite needs to know whether the source has URLs at all.

Where the ticket is filed is never written into it. The directory is the
record of that, so moving the directory can never leave a stale copy behind.
What is written is the ticket's own `coordinates` — where it lives upstream —
because those do not change when it is filed somewhere else.
"""

from datetime import datetime, timezone
from pathlib import Path

from . import config, layout, paths
from .layout import Location, Scope

FILENAME = "ticket.json"


def path_for(location: Location) -> Path:
    return location.dir / FILENAME


def load(location: Location) -> dict:
    return config.read_json(path_for(location))


def save(location: Location, data: dict) -> None:
    config.write_json(path_for(location), data)


def update(location: Location, **changes) -> dict:
    """
    Merge changes into ticket.json, creating it when absent.

    A key passed as None is written as null rather than skipped. `url` is the
    reason: a source with no web address has to say so explicitly, because an
    absent key reads as "not fetched yet" while an explicit null reads as
    "this source has none" — and only the second is true.
    """
    record = load(location)
    record.setdefault("source", location.source)
    record.setdefault("id", location.id)
    record.update(changes)
    save(location, record)
    return record


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def on_disk(location: Location, usable: bool) -> dict:
    """
    What of the ticket directory actually exists, so a driver can stop early.

    `config` is whether the source is usable where this ticket is filed:
    every coordinate its manifest declares is known, from the bindings or the
    ticket itself. A source that declares none is always usable.
    """
    root = location.dir
    raw_dir = root / "raw"
    return {
        "ticket_dir": root.is_dir(),
        "ticket_json": (root / FILENAME).is_file(),
        "digest": (root / "digest.md").is_file(),
        "plan": plan_index(root).is_file(),
        # MIGRATION: removed with ticket-plan/MIGRATION.md.
        "legacy_plan": is_legacy_plan(root),
        "journal": (root / "journal.md").is_file(),
        "raw": raw_dir.is_dir() and any(raw_dir.iterdir()),
        "artifacts": (root / "artifacts").is_dir(),
        "config": usable,
    }


def plan_index(root: Path) -> Path:
    return root / paths.PLAN_DIRNAME / paths.PLAN_INDEX


def is_legacy_plan(root: Path) -> bool:
    """
    A single-file `plan.md` at the ticket root, from before plans became a directory.

    MIGRATION: `/ticket-plan` converts it; remove this once none is left —
    see ticket-plan/MIGRATION.md.
    """
    return (root / paths.PLAN_INDEX).is_file() and not plan_index(root).is_file()


def list_all(scope: Scope | None = None) -> list[dict]:
    """
    Every ticket on disk, optionally narrowed to a scope, newest first.

    This is what a driver prints when it has to ask which ticket the user
    means — the Product and Source columns are why it spans every one of them.
    """
    entries: list[dict] = []
    for location in layout.locations(scope=scope):
        record = load(location)
        root = location.dir
        entries.append(
            {
                "namespace": location.product.namespace,
                "product": location.product.ref,
                "source": location.source,
                "id": location.id,
                "ref": location.ref,
                "qualified_ref": location.qualified,
                "title": record.get("title"),
                "type": record.get("type"),
                "state": record.get("state"),
                "url": record.get("url"),
                "parent": record.get("parent"),
                "path": str(root),
                "last_touched": newest_mtime(root),
                "has_plan": plan_index(root).is_file(),
                "has_journal": (root / "journal.md").is_file(),
                "has_digest": (root / "digest.md").is_file(),
            }
        )

    entries.sort(key=lambda entry: entry["last_touched"] or "", reverse=True)
    return entries


def newest_mtime(directory: Path) -> str | None:
    newest = 0.0
    for path in (
        directory / "journal.md",
        plan_index(directory),
        directory / "digest.md",
        directory / FILENAME,
    ):
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
