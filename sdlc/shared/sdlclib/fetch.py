"""
`fetch`: mirror a ticket from its source into the ticket's `raw/` directory,
and its journal entries upstream into `journal/`.

The ticket is found, or filed, by the same logic `resolve` uses, so a ticket's
own coordinates win over any binding and a first fetch lands under the bound
product. The source's fetcher writes `raw/` and returns the fields the source
determines; this module records them in `ticket.json` and leaves every other
key alone, which is how a `type` the model recorded survives a refresh.

Nothing is written when the source cannot be read: a half-mirrored ticket
would read as a complete one.
"""

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import NotRequired, TypedDict

from . import config as configuration
from . import filing, journal, layout, providers, resolve
from .config import Config, describe
from .errors import EXIT_AMBIGUOUS, SdlcError
from .layout import Scope

FETCHED_FIELDS = ("title", "state", "url", "fingerprint")


class FetchReport(resolve.ResolveReport):
    fetched: dict


class CheckReport(TypedDict):
    ref: str
    ticket_dir: str
    changed: bool
    status: str
    recorded: dict | None
    live: dict | None
    reason: NotRequired[str]
    coordinates: NotRequired[dict[str, str]]
    last_fetched_at: NotRequired[str | None]
    journal: NotRequired[dict]
    only_journal: NotRequired[bool]


def read_record(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise SdlcError(f"{path}: is not a valid ticket record ({error})") from error
    if not isinstance(record, dict):
        raise SdlcError(f"{path}: must hold a JSON object")
    return record


def write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_suffix(".json.tmp")
    scratch.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(scratch, path)


def read_mirror(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise SdlcError(
            f"{path}: is not a readable mirror ({error})",
            hint="Refresh it with `/sdlc:intake`.",
        ) from error


def bound_namespace_value(
    config: Config, source: str, name: str, context: Scope | None
) -> str:
    """The one value of a namespace-level coordinate to read upstream with, from the bindings."""
    searched = [[context.namespace] if context else [], sorted(config.namespaces)]
    for namespaces in searched:
        values: dict[str, str] = {}
        for namespace in namespaces:
            value = config.namespace_binding(source, namespace).get(name)
            if value:
                values.setdefault(value.casefold(), value)
        if len(values) == 1:
            return next(iter(values.values()))
        if len(values) > 1:
            raise SdlcError(
                f"more than one {source} {name} is bound: {', '.join(sorted(values.values()))}",
                EXIT_AMBIGUOUS,
                f"Pass --context namespace, or --coordinate {name}=...",
            )
    raise SdlcError(
        f"no {source} {name} is bound, so there is nowhere to read the ticket from",
        hint=f"Run `/sdlc:setup` to bind {source}, or pass --coordinate {name}=...",
    )


def require_bound_product(config: Config, source: str, found: dict[str, str]) -> None:
    """
    A ticket's own coordinates must name a product, never fall back to a default one.

    Nothing moves a ticket after it is filed, so a work item filed under
    `default` because its project was unbound could only be fixed by hand.
    """
    if not any(
        not product.is_fallback
        and filing.binds_all(config.binding(source, product), found)
        for product in layout.products()
    ):
        raise SdlcError(
            f"no product is bound to {source} {describe(found)}",
            hint="Run `/sdlc:setup` to bind them, naming the namespace and product.",
        )


def discoverer(
    config: Config, context: Scope | None
) -> Callable[[str, str, dict[str, str]], dict[str, str]]:
    """
    Lets a source that cannot tell a ticket's product from its id ask upstream first.

    An Azure DevOps id names no project, so reading it from the work item is
    what files it, the first time, under the product bound to that project.
    """

    def discover(source: str, ticket_id: str, given: dict[str, str]) -> dict[str, str]:
        find = getattr(providers.load_fetcher(source), "discover_coordinates", None)
        declared = providers.coordinates(source)
        if find is None or all(name in given for name in declared):
            return {}
        known = dict(given)
        for name, level in declared.items():
            if level == "namespace" and name not in known:
                known[name] = bound_namespace_value(config, source, name, context)
        found = find(ticket_id, known)
        require_bound_product(config, source, found)
        return found

    return discover


def upstream_coordinates(config: Config, found: resolve.Found) -> dict[str, str]:
    ticket = found.ticket
    if not providers.load_manifest(ticket.source)["capabilities"]["fetch"]:
        raise SdlcError(
            f"{ticket.ref} is a {ticket.source} ticket, which has no upstream to fetch from"
        )

    coordinates = {**resolve.ticket_coordinates(config, ticket), **found.coordinates}
    missing = [
        name for name in providers.coordinates(ticket.source) if name not in coordinates
    ]
    if missing:
        raise SdlcError(
            f"{ticket.product.ref} has no {ticket.source} {', '.join(missing)} to fetch from",
            hint="Bind them with `/sdlc:setup`, or name them with --coordinate.",
        )
    return coordinates


def fetch(
    reference_text: str,
    coordinate_arguments: list[str],
    context_text: str | None,
    cwd: Path,
) -> FetchReport:
    config = configuration.load()
    context = layout.parse_context(context_text)
    found = resolve.locate_existing(
        config,
        resolve.parse_reference(reference_text),
        coordinate_arguments,
        context,
        cwd,
        discoverer(config, context),
    )
    ticket = found.ticket

    coordinates = upstream_coordinates(config, found)

    mirrored = providers.load_fetcher(ticket.source).fetch(
        ticket.id, coordinates, ticket.dir / "raw"
    )

    mirrored_journal = journal.mirror(mirrored["comments"], ticket.dir / "journal")

    record_path = ticket.dir / "ticket.json"
    record = read_record(record_path)
    record.update(source=ticket.source, id=ticket.id, coordinates=coordinates)
    record.update({field: mirrored[field] for field in FETCHED_FIELDS})
    record["last_fetched_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    write_record(record_path, record)

    return FetchReport(
        **resolve.report(
            config,
            ticket,
            exists=found.exists,
            context=context,
            chosen=found.chosen,
        ),
        fetched={**mirrored["report"], "journal": mirrored_journal},
    )


def check(
    reference_text: str,
    coordinate_arguments: list[str],
    context_text: str | None,
    cwd: Path,
) -> CheckReport:
    """
    Whether the ticket changed upstream since it was mirrored, writing nothing.

    `changed` is true for a ticket never mirrored too: with no recorded
    revision there is nothing to vouch that the mirror matches upstream, which
    is the safe answer for a caller about to write upstream. `status` tells the
    cases apart. `stale_mirror` is a recorded revision with no `raw/raw.json`
    (what a mirror from before that shape lacks); it is answered without
    asking upstream. `journal` and `only_journal` are defined in `journal.md`.
    """
    config = configuration.load()
    context = layout.parse_context(context_text)
    found = resolve.locate_existing(
        config,
        resolve.parse_reference(reference_text),
        coordinate_arguments,
        context,
        cwd,
    )
    ticket = found.ticket
    report: CheckReport = {
        "ref": ticket.ref,
        "ticket_dir": str(ticket.dir),
        "recorded": None,
        "live": None,
        "changed": False,
        "status": "local",
    }

    if not providers.load_manifest(ticket.source)["capabilities"]["fetch"]:
        report["reason"] = (
            f"a {ticket.source} ticket has no upstream, so nothing can change under it"
        )
        return report

    record = read_record(ticket.dir / "ticket.json") if found.exists else {}
    recorded = record.get("fingerprint")
    if not recorded:
        report.update(changed=True, status="never_mirrored")
        report["reason"] = (
            f"{ticket.ref} has never been fetched, so there is no recorded revision to compare"
        )
        return report

    if not (ticket.dir / "raw" / "raw.json").is_file():
        # A mirror from before the current shape holds a revision that still
        # matches upstream, yet `resume` and `submit` read `raw/raw.json`.
        report.update(changed=True, status="stale_mirror", recorded=recorded)
        report["reason"] = (
            f"the mirror of {ticket.ref} is in an older shape that lacks raw/raw.json; "
            f"refresh it with `/sdlc:intake {ticket.ref}`"
        )
        return report

    mirror = read_mirror(ticket.dir / "raw" / "raw.json")
    coordinates = upstream_coordinates(config, found)
    fetcher = providers.load_fetcher(ticket.source)
    answer = fetcher.check(ticket.id, coordinates, mirror)
    live = answer["fingerprint"]
    upstream = answer.get("upstream")
    changed = live != recorded
    report.update(
        changed=changed,
        status="changed" if changed else "unchanged",
        recorded=recorded,
        live=live,
    )
    report["coordinates"] = coordinates
    report["last_fetched_at"] = record.get("last_fetched_at")
    report["journal"] = journal.compare(
        fetcher.comments_of(upstream or mirror), ticket.dir / "journal"
    )
    if changed:
        # Every checkpoint posts a comment, which moves the revision; telling
        # that apart keeps `resume` from calling for a refresh after each one.
        report["only_journal"] = upstream is not None and fetcher.signature(
            upstream
        ) == fetcher.signature(mirror)
    return report
