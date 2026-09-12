#!/usr/bin/env python3
"""
Turning a reference the user typed into a source, an id and a set of paths.

The resolution order is implemented here once and restated in prose nowhere:

1. An explicit prefix — `ado:12345`, `gh:42`, `local:auth-fix`
2. A bare token — scan every source for a ticket directory of that name;
   exactly one hit wins, two or more is an error that lists them
3. The root config's `default_source`
"""

import re

from . import config, paths, providers, tickets
from .errors import (
    EXIT_AMBIGUOUS,
    EXIT_ERROR,
    EXIT_LEGACY_LAYOUT,
    EXIT_REQUIRE_UNMET,
    TicketError,
)

LEGACY_HINT = (
    "The pre-`~/.tickets` layout is still on disk at {legacy}. "
    "Run `/ticket-init` to migrate it."
)

# What `--require` accepts, mapped onto the survey `tickets.on_disk` returns.
REQUIREMENTS = (
    "config",
    "ticket_dir",
    "ticket_json",
    "raw",
    "digest",
    "plan",
    "journal",
)


def prefix_map() -> dict[str, str]:
    """Every accepted prefix, including each source's own name."""
    mapping: dict[str, str] = {}
    for source in providers.list_sources():
        mapping[source] = source
        for prefix in providers.load_manifest(source).get("prefixes") or []:
            mapping[str(prefix).lower()] = source
    return mapping


def split_ref(ref: str) -> tuple[str | None, str]:
    """Split `prefix:token`, leaving an unprefixed reference's prefix as None."""
    if ":" not in ref:
        return None, ref.strip()

    head, _, tail = ref.partition(":")
    head = head.strip().lower()
    known = prefix_map()
    if head in known:
        return known[head], tail.strip()

    raise TicketError(
        f"unknown source prefix '{head}' in '{ref}'",
        EXIT_ERROR,
        "Known prefixes: " + (", ".join(sorted(known)) or "none") + ".",
    )


def directories_holding(token: str) -> list[str]:
    """Every source with a ticket directory of this name, in listing order."""
    return [
        source
        for source in providers.list_sources()
        if paths.ticket_dir(source, token).is_dir()
    ]


def check_legacy(token: str) -> None:
    """
    Exit 4 rather than "not found" whenever the old layout explains the absence.

    This branch is what lets every driver and every deprecated alias stay
    ignorant of the pre-`~/.tickets` path: they never test for it, they only
    report the code.
    """
    legacy = paths.legacy_home()
    if not legacy.is_dir():
        return

    if (legacy / token).is_dir() or not paths.tickets_home().is_dir():
        raise TicketError(
            f"'{token}' is not under {paths.tickets_home()}, "
            "but the legacy layout is present",
            EXIT_LEGACY_LAYOUT,
            LEGACY_HINT.format(legacy=legacy),
        )


def known_sources_hint() -> str:
    return "Known sources: " + (", ".join(providers.list_sources()) or "none") + "."


def validate_id(source: str, ticket_id: str) -> None:
    manifest = providers.load_manifest(source)
    pattern = (manifest.get("id") or {}).get("pattern")
    if not pattern:
        return
    if not re.fullmatch(pattern, ticket_id):
        noun = (manifest.get("nouns") or {}).get("singular", "ticket")
        raise TicketError(
            f"'{ticket_id}' is not a valid {source} {noun} id",
            EXIT_ERROR,
            f"Ids for this source match {pattern}.",
        )


def require_installed(source: str, reason: str) -> None:
    if source not in providers.list_sources():
        raise TicketError(
            f"{reason} '{source}', which is not installed",
            EXIT_ERROR,
            known_sources_hint(),
        )


def resolve_source(ref: str | None, explicit_source: str | None) -> tuple[str, str]:
    """Returns (source, ticket_id); the id is empty when only a source is named."""
    known = providers.list_sources()
    if not known:
        raise TicketError(
            "no sources are installed",
            EXIT_ERROR,
            "Expected at least one provider directory under "
            f"{providers.providers_root()}.",
        )

    if explicit_source:
        require_installed(explicit_source, "--source names")

    if ref is None:
        source = explicit_source or config.default_source() or ""
        if not source:
            raise TicketError(
                "no source given and no default_source is configured",
                EXIT_ERROR,
                "Pass --source, or run `/ticket-init` to set one. "
                + known_sources_hint(),
            )
        require_installed(source, "default_source is")
        return source, ""

    prefix_source, token = split_ref(ref)
    if not token:
        raise TicketError(f"'{ref}' carries no ticket id", EXIT_ERROR)

    if prefix_source and explicit_source and prefix_source != explicit_source:
        raise TicketError(
            f"'{ref}' names source '{prefix_source}' "
            f"but --source says '{explicit_source}'",
            EXIT_ERROR,
        )

    if prefix_source:
        source = prefix_source
    elif explicit_source:
        source = explicit_source
    else:
        source = resolve_bare(token)

    validate_id(source, token)
    return source, token


def resolve_bare(token: str) -> str:
    """A reference with no prefix: what is on disk decides, then the default."""
    matches = directories_holding(token)

    if len(matches) > 1:
        listing = "\n".join(
            f"  {name}:{token} — {paths.ticket_dir(name, token)}" for name in matches
        )
        raise TicketError(
            f"'{token}' exists in more than one source",
            EXIT_AMBIGUOUS,
            f"Name the source explicitly:\n{listing}",
        )

    if matches:
        return matches[0]

    check_legacy(token)

    source = config.default_source() or ""
    if not source:
        raise TicketError(
            f"'{token}' is not on disk and no default_source is configured",
            EXIT_ERROR,
            "Prefix the id with a source, or run `/ticket-init`. "
            + known_sources_hint(),
        )
    require_installed(source, "default_source is")
    return source


def describe_source(source: str) -> dict:
    """The source-level half of the resolver output, with no ticket resolved."""
    manifest = providers.load_manifest(source)
    return {
        "source": source,
        "kind": manifest.get("kind"),
        "nouns": manifest.get("nouns") or {},
        "formats": manifest.get("formats") or {},
        "capabilities": manifest.get("capabilities") or {},
        "role_files": providers.role_files(source),
        "provider_dir": str(providers.provider_dir(source)),
        "types_dir": str(providers.types_root()),
        "known_types": providers.list_types(),
    }


def resolve(
    ref: str | None,
    explicit_source: str | None = None,
    type_override: str | None = None,
    require: list[str] | None = None,
) -> dict:
    """The full resolver output — every path absolute, every secret redacted."""
    source, ticket_id = resolve_source(ref, explicit_source)
    resolved = describe_source(source)

    if not ticket_id:
        resolved.update(
            {
                "id": None,
                "paths": {
                    "tickets_home": str(paths.tickets_home()),
                    "source_dir": str(paths.source_dir(source)),
                    "source_config": str(paths.source_config_path(source)),
                },
                "config": config.redact(config.load_source(source)),
                "on_disk": {"config": config.is_initialized(source)},
            }
        )
        return resolved

    record = tickets.load(source, ticket_id)

    if type_override:
        known = providers.list_types()
        if known and type_override not in known:
            raise TicketError(
                f"unknown ticket type '{type_override}'",
                EXIT_ERROR,
                "Known types: " + ", ".join(known) + ".",
            )
        if paths.ticket_dir(source, ticket_id).is_dir():
            record = tickets.update(source, ticket_id, type=type_override)
        else:
            record = {**record, "type": type_override}

    survey = tickets.on_disk(source, ticket_id)
    if not survey["ticket_dir"]:
        check_legacy(ticket_id)

    resolved.update(
        {
            "id": ticket_id,
            "type": record.get("type"),
            "native_type": record.get("native_type"),
            "title": record.get("title"),
            "state": record.get("state"),
            "url": record.get("url"),
            "last_fetched_at": record.get("last_fetched_at"),
            "type_file": type_file_for(record.get("type")),
            "paths": paths.ticket_paths(source, ticket_id),
            "ticket_json": record,
            "config": config.redact(config.load_source(source)),
            "on_disk": survey,
        }
    )

    unmet = [name for name in (require or []) if not survey.get(name)]
    if unmet:
        raise TicketError(
            f"{source}:{ticket_id} is missing " + ", ".join(unmet),
            EXIT_REQUIRE_UNMET,
            requirement_hint(source, ticket_id, unmet),
        )

    return resolved


def type_file_for(ticket_type: str | None) -> str | None:
    if not ticket_type:
        return None
    path = providers.types_root() / f"{ticket_type}.md"
    return str(path) if path.is_file() else None


def requirement_hint(source: str, ticket_id: str, unmet: list[str]) -> str:
    """
    Name the skill that would satisfy each unmet requirement.

    Which skill that is depends on the source: a store that cannot fetch is
    populated by `/ticket-new`, and pointing it at `/ticket-fetch` would send
    the user to a verb that structurally refuses.
    """
    ref = f"{source}:{ticket_id}"
    populate = (
        f"Run `/ticket-fetch {ref}`."
        if providers.has_capability(source, "fetch")
        else f"Run `/ticket-new` to create it — `{source}` has no fetch."
    )
    steps = {
        "config": f"Run `/ticket-init {source}`.",
        "raw": populate,
        "ticket_dir": populate,
        "ticket_json": populate,
        "digest": f"Run `/ticket-digest {ref}`.",
        "plan": f"Run `/ticket-plan {ref}`.",
        "journal": f"Run `/ticket-checkpoint {ref}` to start one.",
    }
    # One populate hint is enough however many of its requirements were unmet.
    seen: list[str] = []
    for name in unmet:
        hint = steps.get(name)
        if hint and hint not in seen:
            seen.append(hint)
    return " ".join(seen)
