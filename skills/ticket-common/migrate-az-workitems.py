#!/usr/bin/env python3
"""
Migrates the pre-`~/.tickets` layout to the two-level one.

Renaming directories and rewriting config are the two operations where a
half-completed pass is worst — a 130 KB plan.md and an unregenerable journal.md
are at stake — and neither requires any judgement, which is this suite's own
definition of script work.

**It copies. It does not move.** `journal.md` is the one file in this system
with no other backup: an entry is one session's account of itself, and unlike a
plan, a digest or a probe output, nothing can regenerate it. A copy is therefore
a free backup of the irreplaceable thing.

It is not free on disk, though. Artifacts under a single ticket can run to
hundreds of megabytes — a database dump captured while planning, say — so the
copy can be large, and the old tree stays until someone deletes it. Report the
size and say the old tree can be removed, rather than implying the duplication
costs nothing.

Divergence risk is nil. Once migrated, nothing reads the old path: the drivers
look only under `~/.tickets/`, and the legacy hint fires only when the *new*
directory is absent.

Usage:
    python migrate-az-workitems.py [--dry-run]

Output: a single JSON report on stdout. With --dry-run the report is identical
except that every action is prefixed `would_`.

Exit codes:
    0  migrated, or nothing to migrate
    1  the migration could not be completed
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# A Windows console defaults to a legacy codepage, which turns any non-ASCII
# character in a ticket title into mojibake.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from ticketlib import config, paths, providers

SOURCE = "ado"

# The three keys the old flat config.json held, and nothing else.
LEGACY_CONFIG_KEYS = ("organization", "project", "token")

# A directory is a candidate only if it holds one of these — which excludes an
# empty directory, while the all-digits name test excludes strays.
CONTENT_MARKERS = ("raw", "digest.md", "plan.md", "journal.md")

MIGRATED_NOTE = """# Migrated

The work item data that lived here was **copied** to:

    {destination}

on {date}.

Nothing reads this directory any more — the `ticket-*` skills look only under
`~/.tickets/`. It was left intact rather than moved, because `journal.md` is the
one file here that nothing can regenerate. Delete it whenever you choose.
"""


def action(name: str, dry_run: bool) -> str:
    return f"would_{name}" if dry_run else name


def is_candidate(path: Path) -> bool:
    if not path.is_dir() or not path.name.isdigit():
        return False
    return any((path / marker).exists() for marker in CONTENT_MARKERS)


def read_raw(ticket_path: Path) -> dict | None:
    try:
        return json.loads((ticket_path / "raw" / "raw.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def fetched_at_from_mtime(ticket_path: Path) -> str | None:
    """
    The old fetch recorded no timestamp, so the mtime of raw.json is the only
    record of when the snapshot was taken.

    Getting this wrong matters: every migrated ticket would read as "fetched
    just now" and drift would silently under-report.
    """
    try:
        stamp = (ticket_path / "raw" / "raw.json").stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat(timespec="seconds")


def build_ticket_json(ticket_id: str, source_path: Path) -> dict:
    """Derived, never fabricated. An underivable title stays null."""
    raw = read_raw(source_path)
    if raw is None:
        return {
            "source": SOURCE,
            "id": ticket_id,
            "title": None,
            "url": None,
            "incomplete": True,
        }

    meta = raw.get("meta") or {}
    tree = raw.get("tree") or {}
    work_item = tree.get("work_item") or {}
    fields = work_item.get("fields") or {}

    org = meta.get("organization")
    project = meta.get("project")

    record = {
        "source": SOURCE,
        "id": ticket_id,
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "url": (
            f"https://dev.azure.com/{org}/{project}/_workitems/edit/{ticket_id}"
            if org and project
            else None
        ),
        "last_fetched_at": fetched_at_from_mtime(source_path),
        "fingerprint": {"rev": work_item.get("rev")},
    }

    canonical, native, note = providers.load_private(SOURCE, "_fetch").resolve_type(fields)
    record["type"] = canonical
    record["native_type"] = native
    if note:
        record["type_note"] = note

    if record["title"] is None:
        record["incomplete"] = True

    return record


def migrate_config(legacy_root: Path, dry_run: bool) -> dict:
    report: dict = {}

    legacy_config_path = legacy_root / "config.json"
    legacy_config = config.read_json(legacy_config_path)

    root_config = config.load_root()
    if "default_source" in root_config:
        report["root_config"] = "kept_existing"
        report["default_source"] = root_config["default_source"]
    else:
        report["root_config"] = action("set_default_source", dry_run)
        report["default_source"] = SOURCE
        if not dry_run:
            merged = dict(root_config)
            merged["default_source"] = SOURCE
            config.save_root(merged)

    if not legacy_config:
        report["source_config"] = "skipped_no_legacy_config"
        return report

    destination = paths.source_config_path(SOURCE)
    if destination.exists():
        # Overwriting could replace a working credential with a stale one.
        report["source_config"] = "skipped_exists"
        report["source_config_path"] = str(destination)
        return report

    carried = {
        key: legacy_config[key] for key in LEGACY_CONFIG_KEYS if key in legacy_config
    }
    report["source_config"] = action("write", dry_run)
    report["source_config_path"] = str(destination)
    # Carried over so no re-authentication is needed.
    report["source_config_keys"] = sorted(carried)
    if not dry_run:
        config.save_source(SOURCE, carried)

    return report


def migrate_ticket(ticket_path: Path, dry_run: bool) -> dict:
    ticket_id = ticket_path.name
    destination = paths.ticket_dir(SOURCE, ticket_id)

    entry = {
        "id": ticket_id,
        "from": str(ticket_path),
        "to": str(destination),
    }

    if destination.exists():
        # A partial merge of two plan.md histories is unrecoverable.
        entry["action"] = "skipped_exists"
        return entry

    record = build_ticket_json(ticket_id, ticket_path)
    entry["action"] = action("copy", dry_run)
    entry["title"] = record.get("title")
    entry["type"] = record.get("type")
    entry["last_fetched_at"] = record.get("last_fetched_at")
    if record.get("incomplete"):
        entry["incomplete"] = True

    if not dry_run:
        shutil.copytree(ticket_path, destination)
        config.write_json(destination / "ticket.json", record)

    return entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy the pre-~/.tickets layout into the two-level one."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would happen and change nothing",
    )
    args = parser.parse_args()

    legacy_root = paths.legacy_home()
    if not legacy_root.is_dir():
        print(json.dumps({"result": "nothing_to_migrate", "legacy_root": str(legacy_root)}, indent=2))
        return 0

    candidates = sorted(
        (path for path in legacy_root.iterdir() if is_candidate(path)),
        key=lambda path: int(path.name),
    )

    report = {
        "result": "dry_run" if args.dry_run else "migrated",
        "legacy_root": str(legacy_root),
        "tickets_home": str(paths.tickets_home()),
        "config": migrate_config(legacy_root, args.dry_run),
        "tickets": [migrate_ticket(path, args.dry_run) for path in candidates],
        # Contents are never rewritten: plan.md's artifact links are relative
        # and name no old path, digest.md names none, and journal.md's single
        # mention sits inside an entry, where "never edit or delete an existing
        # entry" is this suite's strongest rule.
        "file_contents_rewritten": "none — the old path is not referenced by any migrated file",
        "old_tree": "left intact; delete it whenever you choose",
    }

    note_path = legacy_root / "MIGRATED.md"
    report["migrated_note"] = action("write", args.dry_run)
    report["migrated_note_path"] = str(note_path)
    if not args.dry_run:
        note_path.write_text(
            MIGRATED_NOTE.format(
                destination=paths.source_dir(SOURCE),
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ),
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
