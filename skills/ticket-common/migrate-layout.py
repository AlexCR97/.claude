#!/usr/bin/env python3
"""
Migrates the `{source}/{id}` layout to `{namespace}/{product}/{source}/{id}`.

**It renames. It does not copy.** Unlike the migration out of `~/.az-workitems`,
source and destination are on the same disk, so each ticket directory moves in
one rename that carries every byte of `journal.md` or none of it. A copy would
only double what is on disk — artifacts can run to hundreds of megabytes — and
leave two trees to diverge.

Each source's tickets are filed together under one product: the one its old
config's coordinates name, or the one `--map` gives. Keeping a source's
tickets together is what keeps the relative links between siblings working.
A ticket whose own coordinates disagree with that product's binding goes to a
`default` product instead, because a ticket is never filed against its identity.

It is safe to re-run after an interruption. Bindings and credentials are
merged rather than replaced, a ticket already moved is simply not found in the
old place again, a link is only rewritten while it is still broken, and
`layout: 2` is recorded last — so an unfinished pass keeps every skill
refusing with exit 4 until it is finished.

Usage:
    python migrate-layout.py [--dry-run] [--map SOURCE=NAMESPACE/PRODUCT ...]

Output: a single JSON report on stdout. With --dry-run the report is identical
except that every action is prefixed `would_`.

Exit codes:
    0  migrated, or nothing to migrate
    1  the migration could not be completed
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")

from ticketlib import (
    bindings,
    config,
    filing,
    layout,
    links,
    paths,
    providers,
    sources,
    tickets,
    tokencache,
)
from ticketlib.errors import TicketError
from ticketlib.layout import Location, Product


@dataclass
class Move:
    source: str
    id: str
    old_dir: Path
    location: Location
    coordinates: dict
    action: str
    note: str | None = None
    error: str | None = None


@dataclass
class Group:
    source: str
    old_dir: Path
    product: Product
    mapped: bool
    binding: dict
    token: dict | None
    credential_key: str | None
    moves: list[Move] = field(default_factory=list)


def action(name: str, dry_run: bool) -> str:
    return f"would_{name}" if dry_run else name


def parse_maps(raw: list[str]) -> dict[str, Product]:
    maps: dict[str, Product] = {}
    for entry in raw:
        source, equals, target = entry.partition("=")
        if not equals or not source.strip():
            raise TicketError(f"--map '{entry}' is not SOURCE=NAMESPACE/PRODUCT")
        sources.require_installed(source.strip(), "--map names")
        maps[source.strip()] = layout.parse_product(target)
    return maps


def legacy_binding(source: str, legacy: dict) -> dict:
    """The coordinates a layout-1 config held, under the names the manifest declares now."""
    module = providers.load_module(source)
    convert = getattr(module, "binding_from_layout1", None)
    if callable(convert):
        return convert(legacy)
    return {
        name: str(legacy[name])
        for name in providers.coordinates(source)
        if legacy.get(name)
    }


def coordinates_from_url(source: str, url: object) -> dict:
    if not isinstance(url, str) or not url:
        return {}
    for pattern in sources.url_patterns(source):
        match = re.match(pattern, url, re.IGNORECASE)
        if match:
            return {
                name: value
                for name, value in match.groupdict().items()
                if name != "id" and value
            }
    return {}


def plan(maps: dict[str, Product]) -> list[Group]:
    groups: list[Group] = []
    for source in layout.layout1_sources():
        old_dir = paths.layout1_source_dir(source)
        legacy = config.read_json(paths.layout1_source_config_path(source))
        binding = legacy_binding(source, legacy)
        product = maps.get(source) or bindings.derive(source, binding)
        token = legacy.get("token") if isinstance(legacy.get("token"), dict) else None

        group = Group(
            source,
            old_dir,
            product,
            source in maps,
            binding,
            token,
            providers.credential_key(source, binding),
        )

        at_namespace, at_product = bindings.levels(source, product, binding)
        will_bind = {
            **config.binding(source, product.namespace, product.name),
            **at_namespace,
            **at_product,
        }
        for entry in sorted(old_dir.iterdir()):
            if not entry.is_dir():
                continue
            record = config.read_json(entry / tickets.FILENAME)
            own = {}
            if providers.coordinates(source):
                own = record.get("coordinates") or coordinates_from_url(
                    source, record.get("url")
                )

            filed_under, note = product, None
            if own and filing.conflicts(will_bind, own):
                filed_under = fallback_for(source, own, product)
                note = (
                    f"its own coordinates ({filing.describe(own)}) disagree with "
                    f"{product.ref}'s binding, so it is filed under {filed_under.ref}"
                )

            location = Location(filed_under, source, entry.name)
            group.moves.append(
                Move(
                    source,
                    entry.name,
                    entry,
                    location,
                    own,
                    "skipped_exists" if location.dir.exists() else "move",
                    note,
                )
            )
        groups.append(group)
    return groups


def fallback_for(source: str, own: dict, product: Product) -> Product:
    """The target namespace's `default` product when the namespace still matches, else `default/default`."""
    at_namespace, _ = providers.split_by_level(source, own)
    bound = config.binding(source, product.namespace, None)
    if at_namespace and not filing.conflicts(bound, at_namespace):
        return Product(product.namespace, paths.DEFAULT_NAME)
    return Product(paths.DEFAULT_NAME, paths.DEFAULT_NAME)


def remap(path: Path, pairs: list[tuple[Path, Path]]) -> Path:
    for old, new in pairs:
        try:
            return new / path.relative_to(old)
        except ValueError:
            continue
    return path


def relink(pairs: list[tuple[Path, Path]], dry_run: bool) -> dict:
    """
    Repair every link the move broke, in the files a repair is allowed to touch.

    `pairs` maps each ticket's layout-1 directory to its new one. In a dry run
    nothing has moved yet, so a post-move path is answered by mapping it back
    onto where it still sits.
    """
    home = paths.tickets_home()
    backwards = [(new, old) for old, new in pairs]

    def to_new(path: Path) -> Path:
        return remap(path, pairs)

    def exists(path: Path) -> bool:
        return (remap(path, backwards) if dry_run else path).exists()

    report: dict[str, list] = {
        "links_rewritten": [],
        "links_left_broken": [],
        "links_already_broken": [],
        "absolute_path_mentions": [],
    }
    for old_dir, new_dir in pairs:
        here = old_dir if dry_run else new_dir
        if not here.is_dir():
            continue
        for path in links.markdown_files(here):
            relative = path.relative_to(here)
            old_file, new_file = old_dir / relative, new_dir / relative
            # Untranslated line endings, so a repaired link is the only byte that changes.
            with path.open(encoding="utf-8", errors="replace", newline="") as handle:
                text = handle.read()

            found = links.analyze(text, old_file, new_file, to_new, exists, home)
            broken = [item for item in found if item.status == "broken_by_move"]
            if not links.in_snapshot(new_file, new_dir):
                report["links_already_broken"].extend(
                    item.as_dict() for item in found if item.status == "already_broken"
                )

            if broken and links.is_rewritable(new_file, new_dir):
                if not dry_run:
                    with path.open("w", encoding="utf-8", newline="") as handle:
                        handle.write(links.rewrite(text, broken))
                report["links_rewritten"].extend(
                    {**item.as_dict(), "action": action("rewrite", dry_run)}
                    for item in broken
                )
            else:
                report["links_left_broken"].extend(
                    {**item.as_dict(), "reason": "journal.md and raw/ are never edited"}
                    for item in broken
                )

            if links.mentions(text, old_dir):
                report["absolute_path_mentions"].append(str(new_file))

    return report


def execute(groups: list[Group], dry_run: bool) -> dict:
    source_reports = []
    for group in groups:
        at_namespace, at_product = bindings.levels(
            group.source, group.product, group.binding
        )
        entry: dict = {
            "source": group.source,
            "from": str(group.old_dir),
            "product": group.product.ref,
            "mapped": group.mapped,
            "binding": {"namespace": at_namespace, "product": at_product},
            "binding_action": (
                action("write", dry_run) if at_namespace or at_product else "none"
            ),
        }
        if not dry_run:
            bindings.write(group.source, group.product, group.binding)
            group.product.dir.mkdir(parents=True, exist_ok=True)

        if group.token and group.credential_key:
            target = paths.credentials_path(group.source, group.credential_key)
            entry["credential"] = (
                "skipped_exists" if target.exists() else action("move", dry_run)
            )
            entry["credential_path"] = str(target)
            if not dry_run and not target.exists():
                tokencache.save(group.source, group.credential_key, group.token)
        else:
            entry["credential"] = "none"

        for move in group.moves:
            if dry_run or move.action != "move":
                continue
            move.location.dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.rename(move.old_dir, move.location.dir)
            except OSError as exc:
                # One ticket held open must not cost the report of every other:
                # it stays where it was, and the pass ends incomplete.
                move.action = "failed"
                move.error = str(exc)
                continue
            if move.coordinates:
                tickets.update(move.location, coordinates=move.coordinates)

        source_reports.append(entry)

    return {"sources": source_reports}


def clean_up(groups: list[Group], dry_run: bool) -> dict:
    """Remove each old source directory once nothing is left in it but its config."""
    removed, kept = [], []
    for group in groups:
        legacy_config = paths.layout1_source_config_path(group.source)
        remaining = [
            entry.name
            for entry in (group.old_dir.iterdir() if group.old_dir.is_dir() else [])
            if entry != legacy_config
        ]
        if dry_run:
            pending = [move.id for move in group.moves if move.action != "move"]
            (kept if pending else removed).append(
                {
                    "dir": str(group.old_dir),
                    "action": action("remove", dry_run) if not pending else "kept",
                    "remaining": pending,
                }
            )
            continue
        if remaining:
            kept.append(
                {"dir": str(group.old_dir), "action": "kept", "remaining": remaining}
            )
            continue
        try:
            legacy_config.unlink(missing_ok=True)
            group.old_dir.rmdir()
        except OSError as exc:
            kept.append(
                {"dir": str(group.old_dir), "action": "kept", "error": str(exc)}
            )
            continue
        removed.append({"dir": str(group.old_dir), "action": "remove"})
    return {"old_dirs_removed": removed, "old_dirs_kept": kept}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move the {source}/{id} layout under namespaces and products."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would happen and change nothing",
    )
    parser.add_argument(
        "--map", action="append", default=[], metavar="SOURCE=NAMESPACE/PRODUCT"
    )
    args = parser.parse_args()

    try:
        maps = parse_maps(args.map)
        if not layout.layout1_sources():
            print(
                json.dumps(
                    {
                        "result": "nothing_to_migrate",
                        "tickets_home": str(paths.tickets_home()),
                    },
                    indent=2,
                )
            )
            return 0

        groups = plan(maps)
        report: dict = {
            "result": "dry_run" if args.dry_run else "migrated",
            "tickets_home": str(paths.tickets_home()),
            "layout": {"from": layout.version() or 1, "to": layout.LAYOUT_VERSION},
        }
        pairs = [
            (move.old_dir, move.location.dir)
            for group in groups
            for move in group.moves
            if move.action == "move"
        ]

        report.update(execute(groups, args.dry_run))
        report["tickets"] = [
            {
                "from": str(move.old_dir),
                "to": str(move.location.dir),
                "qualified_ref": move.location.qualified,
                "action": action(move.action, args.dry_run)
                if move.action == "move"
                else move.action,
                **({"note": move.note} if move.note else {}),
                **({"error": move.error} if move.error else {}),
            }
            for group in groups
            for move in group.moves
        ]

        if not args.dry_run:
            # Every ticket now in the new layout, not only this run's: a re-run
            # after an interruption still owes the earlier run's repairs.
            pairs = [
                (paths.layout1_ticket_dir(location.source, location.id), location.dir)
                for location in layout.locations()
            ]
        report.update(relink(pairs, args.dry_run))
        report.update(clean_up(groups, args.dry_run))

        if not args.dry_run:
            if layout.layout1_sources():
                report["result"] = "incomplete"
                failed = any(
                    move.action == "failed" for group in groups for move in group.moves
                )
                report["hint"] = (
                    "Some old directories still hold tickets that could not be moved; "
                    "see old_dirs_kept"
                    + (
                        " and each ticket whose action is `failed`. A directory that cannot "
                        "be renamed is usually held open — a terminal or an editor with its "
                        "working directory inside it. Close it"
                        if failed
                        else ". Resolve them by hand"
                    )
                    + ", then re-run the migration."
                )
            else:
                config.update_level({"layout": layout.LAYOUT_VERSION})

        report["copied"] = "nothing — every ticket directory was renamed in place"
    except TicketError as exc:
        print(f"ERROR: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(exc.hint, file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
