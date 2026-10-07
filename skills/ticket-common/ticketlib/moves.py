#!/usr/bin/env python3
"""
Re-filing a ticket under another product.

The directory is renamed, never copied: `journal.md` cannot be regenerated,
and a rename carries every byte of it or none. What a rename cannot carry is
anything that pointed at the old place. A `parent` reference is data the suite
resolves, so it is rewritten — on the moved ticket and on every child that
names it. A link in prose is reported instead: a journal entry is never edited,
and the rest is someone's writing.
"""

import os
from pathlib import Path

from . import config, filing, layout, links, paths, providers, sources, tickets
from .errors import EXIT_ERROR, TicketError
from .layout import Location, Product


def move(location: Location, target: Product, dry_run: bool) -> dict:
    if target == location.product:
        raise TicketError(
            f"{location.qualified} is already filed under {target.ref}", EXIT_ERROR
        )
    if not location.dir.is_dir():
        raise TicketError(f"{location.qualified} is not on disk", EXIT_ERROR)

    dest = Location(target, location.source, location.id)
    if dest.dir.exists():
        raise TicketError(
            f"{dest.qualified} already exists",
            EXIT_ERROR,
            "A move never merges into an existing ticket directory.",
        )

    record = tickets.load(location)
    coordinates = identity(location, record)
    mismatch = filing.conflicts(
        config.binding(location.source, target.namespace, target.name), coordinates
    )
    if mismatch:
        detail = "; ".join(
            f"{name} is '{bound}' there, '{given}' on the ticket"
            for name, (bound, given) in mismatch.items()
        )
        raise TicketError(
            f"{target.ref} is bound to other {location.source} coordinates — {detail}",
            EXIT_ERROR,
            "A ticket is never filed against its own coordinates.",
        )

    references, unresolved = reference_changes(location, dest, record)
    relinks, mentioned = link_report(location, dest)

    report = {
        "result": "dry_run" if dry_run else "moved",
        "from": location.qualified,
        "to": dest.qualified,
        "from_dir": str(location.dir),
        "to_dir": str(dest.dir),
        "references": [
            {
                "ticket": (dest if change[0] == location else change[0]).qualified,
                "from": change[1],
                "to": change[2],
            }
            for change in references
        ],
        "unresolved_parent": unresolved,
        "links_broken_by_move": [
            relink.as_dict() for relink in relinks if relink.status == "broken_by_move"
        ],
        "links_already_broken": [
            relink.as_dict() for relink in relinks if relink.status == "already_broken"
        ],
        "absolute_path_mentions": [str(path) for path in mentioned],
    }

    # Every rewrite is tried first without writing, while each ticket is still
    # where it was: a body that cannot take one stops the move before anything
    # has changed, rather than half-way through it. A dry run is refused the same way.
    for ticket, _, new_ref in references:
        rewrite_parent(ticket, new_ref, dry_run=True)
    if dry_run:
        return report

    dest.dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(location.dir, dest.dir)
    except OSError as exc:
        raise TicketError(
            f"could not move {location.dir} — {exc}",
            EXIT_ERROR,
            "Nothing was changed. A directory that cannot be renamed is usually held "
            "open — a terminal or an editor with its working directory inside it. "
            "Close it and try again.",
        ) from exc

    if providers.coordinates(location.source) and coordinates != (
        record.get("coordinates") or {}
    ):
        # Recorded on the way out: the product it came from was what supplied
        # them, and the product it lands in may not.
        tickets.update(dest, coordinates=coordinates)

    # The directory has moved, so a rewrite that fails now is reported rather
    # than raised: stopping here would lose the report of everything else.
    failed = []
    for ticket, _, new_ref in references:
        now = dest if ticket == location else ticket
        try:
            rewrite_parent(now, new_ref, dry_run=False)
        except (TicketError, OSError) as exc:
            failed.append(
                {
                    "ticket": now.qualified,
                    "parent": new_ref,
                    "error": exc.message if isinstance(exc, TicketError) else str(exc),
                }
            )
    if failed:
        report["result"] = "moved_with_errors"
        report["references_failed"] = failed

    return report


def rewrite_parent(ticket: Location, ref: str, dry_run: bool) -> None:
    """
    Point one ticket's stored `parent` at `ref`.

    The source's own record goes first — for a local ticket that is the body
    itself, its source of truth — so a failure leaves `ticket.json` agreeing
    with it rather than ahead of it.
    """
    if providers.has_function(ticket.source, "set_parent"):
        providers.load_module(ticket.source).set_parent(
            sources.provider_context(ticket.source, ticket.product, ticket),
            ref,
            dry_run=dry_run,
        )
    if not dry_run:
        tickets.update(ticket, parent=ref)


def identity(location: Location, record: dict) -> dict:
    """The ticket's own coordinates, as the product it is leaving supplies them."""
    return {
        name: value
        for name, value in sources.ticket_coordinates(location, record).items()
        if name in providers.coordinates(location.source)
    }


def reference_changes(
    location: Location, dest: Location, record: dict
) -> tuple[list[tuple[Location, str, str]], str | None]:
    """Every stored `parent` that would stop resolving, as (ticket, old text, new text)."""
    changes: list[tuple[Location, str, str]] = []
    unresolved = None

    own = record.get("parent")
    if own:
        parent = sources.resolve_stored(own, location.product)
        if parent is None:
            unresolved = own
        elif parent.ref_from(dest.product) != own:
            changes.append((location, own, parent.ref_from(dest.product)))

    for other in layout.locations():
        if other == location:
            continue
        written = tickets.load(other).get("parent")
        if not written or sources.resolve_stored(written, other.product) != location:
            continue
        rewritten = dest.ref_from(other.product)
        if rewritten != written:
            changes.append((other, written, rewritten))

    return changes, unresolved


def link_report(
    location: Location, dest: Location
) -> tuple[list[links.Relink], list[Path]]:
    """
    Links the move breaks — from inside the ticket and into it from elsewhere.

    Worked out before anything moves, so post-move paths are answered by
    mapping them back onto where they sit now.
    """
    home = paths.tickets_home()

    def to_new(path: Path) -> Path:
        return remap(path, location.dir, dest.dir)

    def exists_after(path: Path) -> bool:
        if links.is_inside(path, location.dir):
            return False
        return remap(path, dest.dir, location.dir).exists()

    relinks: list[links.Relink] = []
    mentioned: list[Path] = []

    for ticket in layout.locations():
        for path in links.markdown_files(ticket.dir):
            text = path.read_text(encoding="utf-8", errors="replace")
            if ticket == location:
                new_file = to_new(path)
                relinks.extend(
                    relink
                    for relink in links.analyze(
                        text, path, new_file, to_new, exists_after, home
                    )
                    if relink.status == "broken_by_move"
                    or not links.in_snapshot(path, location.dir)
                )
            else:
                relinks.extend(
                    relink
                    for relink in links.analyze(
                        text, path, path, to_new, exists_after, home
                    )
                    if relink.status == "broken_by_move"
                )
            if links.mentions(text, location.dir):
                mentioned.append(path)

    return relinks, mentioned


def remap(path: Path, old: Path, new: Path) -> Path:
    try:
        return new / path.relative_to(old)
    except ValueError:
        return path
