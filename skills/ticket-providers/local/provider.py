#!/usr/bin/env python3
"""
The local store's entry points.

This provider is the abstraction's stress test: no fetch, no URLs, no
credential. Those gaps are real rather than stubs, and each is declared absent
in provider.json so the front door refuses the verb before any code here runs.

The one relation it does carry — a task's optional link to its parent user
story — has no tree and no reverse index. It lives entirely in `raw/ticket.md`'s
`parent` frontmatter key, validated once here in `new()` and never touched again
by this module.
"""

import argparse
import re
from pathlib import Path

from ticketlib import config, providers, sources, tickets
from ticketlib.errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError

# The heading level `ticket-refine` writes its four synthesized sections at —
# see `refinement-template.md`. Parsing this is safe precisely because it is
# this module's own template shape, not an externally authored format.
REFINEMENT_HEADING_PATTERN = re.compile(r"^#### +(.+?) *$", re.MULTILINE)

# A "TODO — ..." marker sentence, as `new()`'s stubs and `/ticket-new`'s
# type-seeded stub lines both phrase it — up to the first sentence-ending
# punctuation, so a bolded question or a "Provisionally: ..." guess sitting
# next to the marker on the same line survives untouched.
TODO_PATTERN = re.compile(r"TODO\s*[—-]\s*[^.?!]*[.?!]")

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
    parser = argparse.ArgumentParser(prog="ticket.py new --source local")
    parser.add_argument("--parent", help="[source:]id of the parent user story")
    args = parser.parse_args(extra)

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

    parent_ref = resolve_parent(args.parent, resolved_type) if args.parent else None

    frontmatter = {
        "id": ticket_id,
        "title": title,
        "type": resolved_type,
        "state": "New",
        "created": tickets.now_iso(),
        "labels": [],
    }
    if parent_ref:
        frontmatter["parent"] = parent_ref

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _store.render_skeleton(
            frontmatter,
            title,
            DESCRIPTION_STUB,
            ACCEPTANCE_STUB,
        ),
        encoding="utf-8",
    )

    changes = dict(
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
    if parent_ref:
        changes["parent"] = parent_ref
    tickets.update(SOURCE, ticket_id, **changes)

    result = {
        "ticket_file": str(path),
        "type": resolved_type,
        "sections": list(_store.KNOWN_SECTIONS),
    }
    if parent_ref:
        result["parent"] = parent_ref
    return result


def resolve_parent(ref: str, resolved_type: str) -> str:
    """
    Validate a --parent reference and return it in canonical `source:id` form.

    Only a task may carry one, and only a user story may be named as one — the
    one relationship this suite tracks, enforced here because `new()` is the
    only place a local ticket's parent is ever set.
    """
    if resolved_type != "task":
        raise TicketError(
            f"--parent is only valid for a task, not a {resolved_type}",
            EXIT_ERROR,
            "Only a task may have a parent user story.",
        )

    from ticketlib import paths

    parent_source, parent_id = sources.resolve_source(ref, None)
    if not paths.ticket_dir(parent_source, parent_id).is_dir():
        raise TicketError(
            f"parent ticket '{parent_source}:{parent_id}' does not exist",
            EXIT_ERROR,
            "Create the parent user story first, or check the reference.",
        )

    parent_type = tickets.load(parent_source, parent_id).get("type")
    if parent_type and parent_type != "user-story":
        raise TicketError(
            f"parent '{parent_source}:{parent_id}' is a {parent_type}, not a user-story",
            EXIT_ERROR,
            "A task's parent must be a user story.",
        )

    return f"{parent_source}:{parent_id}"


def publish(ctx: dict, text: str, extra: list[str]) -> dict:
    """
    Apply a refinement summary in place rather than posting it as a comment.

    There is no discussion thread to append to that means anything here — the
    ticket file *is* the ticket — so a refinement's conclusions land where
    `new()` left a stub for them: `Goal and Success Criteria` becomes the new
    `Acceptance Criteria`, and the rest becomes `Description`. See `publish.md`.
    """
    path = require_ticket_file(ctx["id"])
    preamble, sections = split_refinement(text)

    acceptance = sections.get("Goal and Success Criteria", "")

    description_blocks = [preamble] if preamble else []
    for heading in ("Domain Model and Data", "Edge Cases and Failure Modes", "Open Items"):
        content = sections.get(heading, "")
        if content:
            description_blocks.append(f"#### {heading}\n\n{content}")
    description = "\n\n".join(description_blocks)

    updated = []
    if acceptance:
        fill_or_grow(path, "Acceptance Criteria", ACCEPTANCE_STUB, acceptance)
        updated.append("Acceptance Criteria")
    if description:
        fill_or_grow(path, "Description", DESCRIPTION_STUB, description)
        updated.append("Description")

    # The body just changed, so the drift fingerprint has to move with it or
    # the next resume would report the refinement as someone else's edit.
    tickets.update(
        SOURCE, ctx["id"], fingerprint={"sha256": _store.fingerprint(path)}
    )

    return {"ticket_file": str(path), "sections_updated": updated, "url": None}


def split_refinement(text: str) -> tuple[str, dict[str, str]]:
    """
    Split a refinement summary into its preamble and its `####` sections.

    Keyed by heading text, exactly as `refinement-template.md` names them.
    """
    matches = list(REFINEMENT_HEADING_PATTERN.finditer(text))
    preamble = text[: matches[0].start()].strip() if matches else text.strip()

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()

    return preamble, sections


def fill_or_grow(path: Path, heading: str, stub: str, content: str) -> None:
    """
    Fill a section still holding its original stub outright; otherwise grow it.

    A local ticket accumulates understanding across repeated refinement passes
    without silently discarding prose a person already wrote by hand — but a
    "TODO — ..." marker is never worth keeping once a refinement has actually
    answered it, so every leftover marker is stripped from what survives first.
    """
    current = strip_todos(_store.section_content(_store.read(path), heading))
    merged = content if not current or current == stub.strip() else f"{current}\n\n{content}"
    if not _store.replace_section(path, heading, merged):
        raise TicketError(f"{path} has no '## {heading}' section")


def strip_todos(text: str) -> str:
    """
    Remove every "TODO — ..." marker sentence, dropping any line — a bare
    paragraph or a bullet — that has nothing left once its marker is gone.

    Only the marker itself is removed. A bolded question or a "Provisionally:
    ..." guess beside it is left in place; it is the "still open" flag that
    goes stale once refinement answers it, not the surrounding context.
    """
    lines = []
    for line in text.splitlines():
        if "TODO" not in line:
            lines.append(line)
            continue

        cleaned = TODO_PATTERN.sub("", line)
        cleaned = re.sub(r"^\s*[-*]\s*$", "", cleaned)  # a bullet with nothing left
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).rstrip()
        if cleaned.strip():
            lines.append(cleaned)
        # else: the whole line was the marker (plus maybe its bullet) — drop it

    result = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return result.strip()


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
    for key in ("id", "title", "state", "type"):
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
