#!/usr/bin/env python3
"""
The local store's entry points.

This provider is the abstraction's stress test: no fetch, no URLs, no related
tickets, no credential. Every one of those is a real gap rather than a stub,
and each is declared absent in provider.json so the front door refuses the verb
before any code here runs.
"""

from datetime import datetime, timezone
from pathlib import Path

from ticketlib import config, providers, tickets
from ticketlib.errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError

SOURCE = "local"

TICKET_FILENAME = "ticket.md"

FALLBACK_TYPE = "task"

DESCRIPTION_STUB = "TODO — what is this, and why now?"
ACCEPTANCE_STUB = "TODO — run `/ticket-refine` to establish these."

_store = providers.load_private(SOURCE, "_store")


def ticket_file(ticket_id: str) -> Path:
    from ticketlib import paths

    return paths.ticket_dir(SOURCE, ticket_id) / "raw" / TICKET_FILENAME


def require_ticket_file(ticket_id: str) -> Path:
    path = ticket_file(ticket_id)
    if not path.is_file():
        raise TicketError(
            f"no ticket body at {path}",
            EXIT_NOT_FOUND,
            f"Run `/ticket-new` to create it.",
        )
    return path


def init(ctx: dict, extra: list[str]) -> dict:
    """
    There is nothing to connect to, so init only makes the store exist.

    The empty config is written rather than skipped: `on_disk.config` is how
    every driver tells "set up" from "never set up", and a local store that
    needs no credential still needs to answer that question.
    """
    from ticketlib import paths

    paths.source_dir(SOURCE).mkdir(parents=True, exist_ok=True)
    if not config.is_initialized(SOURCE):
        config.save_source(SOURCE, {})

    return {
        "store": str(paths.source_dir(SOURCE)),
        "credential": "none — this store is local files",
    }


def new(ctx: dict, title: str, ticket_type: str | None, extra: list[str]) -> dict:
    ticket_id = ctx["id"]
    path = ticket_file(ticket_id)

    if path.exists():
        raise TicketError(f"{path} already exists", EXIT_ERROR)

    resolved_type = ticket_type or FALLBACK_TYPE
    known = providers.list_types()
    if known and resolved_type not in known:
        raise TicketError(
            f"unknown ticket type '{resolved_type}'",
            EXIT_ERROR,
            "Known types: " + ", ".join(known) + ".",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _store.render_skeleton(
            {
                "title": title,
                "type": resolved_type,
                "state": "New",
                "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "labels": [],
            },
            title,
            DESCRIPTION_STUB,
            ACCEPTANCE_STUB,
        ),
        encoding="utf-8",
    )

    tickets.update(
        SOURCE,
        ticket_id,
        title=title,
        state="New",
        type=resolved_type,
        native_type=resolved_type,
        # This store has no web address. Every driver reads `url` and degrades
        # to plain text when it is null, so null is the correct answer here
        # rather than a fabricated file:// path.
        url=None,
        last_fetched_at=tickets.now_iso(),
        fingerprint={"sha256": _store.fingerprint(path)},
    )

    return {
        "ticket_file": str(path),
        "type": resolved_type,
        "sections": list(_store.KNOWN_SECTIONS),
    }


def publish(ctx: dict, text: str, extra: list[str]) -> dict:
    path = require_ticket_file(ctx["id"])
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    _store.append_comment(path, f"### {stamp} UTC — Refinement Session\n\n{text}")

    # The body just changed, so the drift fingerprint has to move with it or
    # the next resume would report the refinement as someone else's edit.
    tickets.update(
        SOURCE, ctx["id"], fingerprint={"sha256": _store.fingerprint(path)}
    )

    return {"ticket_file": str(path), "section": "Comments", "url": None}


def drift(ctx: dict, extra: list[str]) -> dict:
    path = require_ticket_file(ctx["id"])
    record = tickets.load(SOURCE, ctx["id"])

    recorded = (record.get("fingerprint") or {}).get("sha256") or ""
    current = _store.fingerprint(path)
    parsed = _store.read(path)

    return {
        "is_stale": bool(recorded) and recorded != current,
        "ticket_file": str(path),
        "fingerprint": {"recorded": recorded, "current": current},
        "fetched_at": record.get("last_fetched_at"),
        "title": parsed["frontmatter"].get("title") or record.get("title"),
        "state": parsed["frontmatter"].get("state") or record.get("state"),
        "unfingerprinted": not recorded,
        "field_changes": field_changes(record, parsed["frontmatter"]),
        "new_comment_count": 0,
        "new_comments": [],
    }


def field_changes(record: dict, frontmatter: dict) -> list[dict]:
    """What the frontmatter now says that ticket.json still records otherwise."""
    changes = []
    for key in ("title", "state", "type"):
        before = record.get(key)
        after = frontmatter.get(key)
        if after is not None and before != after:
            changes.append({"field": key, "before": before, "after": after})
    return changes


def auth_status(ctx: dict) -> dict:
    from ticketlib import paths

    return {
        "credential": "none — this store is local files",
        "status": "not applicable",
        "usable": True,
        "store": str(paths.source_dir(SOURCE)),
    }
