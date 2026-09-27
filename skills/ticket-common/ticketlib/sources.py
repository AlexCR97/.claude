#!/usr/bin/env python3
"""
Turning a reference the user typed into a ticket's location and a set of paths.

The resolution order is implemented here once and restated in prose nowhere:

1. A web address — matched against the `url.patterns` each source declares.
   Its coordinates decide where it is filed when it is not on disk yet.
2. A qualified reference — `{namespace}/{product}/{source}:{id}` — names one
   directory exactly.
3. `{source}:{id}` or a bare id — the nearest ticket directory of that name:
   in the session context's product, then its namespace, then everywhere.
   Two equally near is an error that lists them; guessing would attach work
   to the wrong ticket.
4. Not on disk anywhere — the ticket is filed by `filing.py`, and a bare id
   takes the effective `default_source`.
"""

import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from . import config, filing, layout, paths, providers, tickets
from .errors import (
    EXIT_AMBIGUOUS,
    EXIT_ERROR,
    EXIT_REQUIRE_UNMET,
    TicketError,
)
from .filing import Filing
from .layout import Location, Product, Scope

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


@dataclass
class Reference:
    """What a typed reference says, before anything on disk is consulted."""

    id: str
    source: str | None = None
    product: Product | None = None
    coordinates: dict = field(default_factory=dict)


@dataclass
class Target:
    """Where a reference points: an existing ticket directory, or where a new one would be filed."""

    location: Location
    filed: bool
    filing: Filing | None = None
    address: dict = field(default_factory=dict)
    outside_context: bool = False


def prefix_map() -> dict[str, str]:
    """Every accepted prefix, including each source's own name."""
    mapping: dict[str, str] = {}
    for source in providers.list_sources():
        mapping[source] = source
        for prefix in providers.load_manifest(source).get("prefixes") or []:
            mapping[str(prefix).lower()] = source
    return mapping


def source_for_prefix(prefix: str, ref: str) -> str:
    known = prefix_map()
    head = prefix.strip().lower()
    if head in known:
        return known[head]
    raise TicketError(
        f"unknown source prefix '{head}' in '{ref}'",
        EXIT_ERROR,
        "Known prefixes: " + (", ".join(sorted(known)) or "none") + ".",
    )


def looks_like_url(ref: str) -> bool:
    return ref.strip().lower().startswith(("http://", "https://"))


def url_patterns(source: str) -> list[str]:
    manifest_url = providers.load_manifest(source).get("url") or {}
    return [str(pattern) for pattern in manifest_url.get("patterns") or []]


def url_hint() -> str:
    accepted = [source for source in providers.list_sources() if url_patterns(source)]
    if not accepted:
        return "No installed source recognises a web address. Pass `{source}:{id}`."
    return (
        "Sources that recognise an address: "
        + ", ".join(accepted)
        + ". Otherwise pass `{source}:{id}`."
    )


def match_url(ref: str) -> Reference:
    """
    A pasted web address -> its source, id and coordinates, by the patterns the manifests declare.

    The patterns live in `provider.json` and not here for the same reason the
    prefixes do: this module must stay ignorant of what any one ticket system's
    addresses look like.
    """
    address = ref.strip()
    for source in providers.list_sources():
        for pattern in url_patterns(source):
            match = re.match(pattern, address, re.IGNORECASE)
            if not match:
                continue
            found = {
                name: urllib.parse.unquote(value)
                for name, value in match.groupdict().items()
                if value is not None
            }
            ticket_id = found.pop("id", "")
            if not ticket_id:
                raise TicketError(
                    f"{source}'s address pattern captured no id from '{ref}'",
                    EXIT_ERROR,
                    "Its `url.patterns` in provider.json needs an `id` group.",
                )
            require_segment(ticket_id, ref)
            return Reference(ticket_id, source, coordinates=found)

    raise TicketError(
        f"no source recognises the address '{ref}'", EXIT_ERROR, url_hint()
    )


def parse(ref: str) -> Reference:
    """`[{namespace}/{product}/][{source}:]{id}`, or a web address."""
    text = ref.strip()
    if looks_like_url(text):
        return match_url(text)

    head, colon, tail = text.partition(":")
    scoped, ticket_id = (head, tail) if colon else ("", head)
    prefix = None

    if colon:
        scope_part, slash, prefix = scoped.rpartition("/")
        scoped = scope_part if slash else ""
    elif "/" in text:
        scoped, _, ticket_id = text.rpartition("/")

    product = None
    if scoped:
        product = layout.parse_scope(scoped).as_product()
        if product is None:
            raise TicketError(
                f"'{ref}' names a namespace but no product",
                EXIT_ERROR,
                "A qualified reference is `{namespace}/{product}/{source}:{id}`.",
            )

    ticket_id = ticket_id.strip()
    if not ticket_id:
        raise TicketError(f"'{ref}' carries no ticket id", EXIT_ERROR)
    require_segment(ticket_id, ref)

    source = source_for_prefix(prefix, ref) if prefix else None
    return Reference(ticket_id, source, product)


def require_segment(ticket_id: str, ref: str) -> None:
    """Refuse an id that is not one path component, before it is joined onto any directory."""
    if not paths.is_segment(ticket_id):
        raise TicketError(
            f"'{ticket_id}' in '{ref}' is not a ticket id",
            EXIT_ERROR,
            "An id is a single name: no `..` and no path separators.",
        )


def known_sources_hint() -> str:
    return "Known sources: " + (", ".join(providers.list_sources()) or "none") + "."


def id_pattern(source: str) -> str | None:
    return (providers.load_manifest(source).get("id") or {}).get("pattern")


def id_matches(source: str, ticket_id: str) -> bool:
    pattern = id_pattern(source)
    return paths.is_segment(ticket_id) and (
        not pattern or bool(re.fullmatch(pattern, ticket_id))
    )


def validate_id(source: str, ticket_id: str) -> None:
    require_segment(ticket_id, ticket_id)
    pattern = id_pattern(source)
    if not pattern:
        return
    if not re.fullmatch(pattern, ticket_id):
        manifest = providers.load_manifest(source)
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


def require_sources() -> None:
    if not providers.list_sources():
        raise TicketError(
            "no sources are installed",
            EXIT_ERROR,
            "Expected at least one provider directory under "
            f"{providers.providers_root()}.",
        )


def optional_scope(text: str | None) -> Scope | None:
    return layout.parse_scope(text) if text else None


def narrow(restrict: Scope | None, product: Product | None, ref: str) -> Scope | None:
    """A qualified reference and `--in` must agree; the reference is the narrower of the two."""
    if product is None:
        return restrict
    if restrict and not restrict.contains(product):
        raise TicketError(
            f"'{ref}' is in {product.ref}, outside --in {restrict.ref}", EXIT_ERROR
        )
    return Scope.of(product)


def ambiguous(ref: str, matches: list[Location]) -> TicketError:
    listing = "\n".join(f"  {match.qualified} — {match.dir}" for match in matches)
    return TicketError(
        f"'{ref}' exists in more than one place",
        EXIT_AMBIGUOUS,
        f"Name it with a qualified reference:\n{listing}",
    )


def find_existing(
    reference: Reference, restrict: Scope | None, prefer: Scope | None, ref: str
) -> Location | None:
    """
    The one ticket directory a reference means, or None when it is on disk nowhere.

    A bare id is only looked for under the sources whose id pattern it fits,
    so a slug is never matched against a directory of numeric ids, or the
    other way round.
    """
    candidates = (
        [reference.source]
        if reference.source
        else [
            source
            for source in providers.list_sources()
            if id_matches(source, reference.id)
        ]
    )
    matches = [
        match
        for source in candidates
        for match in layout.locations(source, reference.id, restrict)
    ]

    if reference.coordinates:
        # The same number in another organization is another ticket.
        matches = [
            match
            for match in matches
            if not filing.conflicts(
                tickets.load(match).get("coordinates") or {}, reference.coordinates
            )
        ]

    matches = layout.nearest(matches, prefer)
    if len(matches) > 1:
        raise ambiguous(ref, matches)
    return matches[0] if matches else None


def resolve_stored(ref: str, own: Product) -> Location | None:
    """
    A reference written inside a ticket — `parent` — resolved from that ticket's own product.

    Nearest first from where the writer was filed is the rule `Location.ref_from`
    writes by, so a short reference means "in my product" and survives the
    whole product being moved together.
    """
    try:
        reference = parse(ref)
    except TicketError:
        return None
    try:
        if reference.source:
            validate_id(reference.source, reference.id)
        return find_existing(
            reference, narrow(None, reference.product, ref), Scope.of(own), ref
        )
    except TicketError:
        return None


def default_source_for(restrict: Scope | None, context: Scope | None) -> str:
    """The effective `default_source` of the nearest scope that says where the ticket goes."""
    for scope in (restrict, context):
        if scope:
            value = config.default_source(scope.namespace, scope.product)
            if value:
                return value
    namespace = config.default_namespace()
    value = config.default_source(namespace, config.default_product(namespace))
    if not value:
        raise TicketError(
            "the id names no source, it is on disk nowhere, and no default_source is configured",
            EXIT_ERROR,
            "Prefix the id with a source, or run `/ticket-setup`. "
            + known_sources_hint(),
        )
    require_installed(value, "default_source is")
    return value


def locate(
    ref: str,
    explicit_source: str | None = None,
    restrict: Scope | None = None,
    context: Scope | None = None,
    cwd: Path | None = None,
) -> Target:
    require_sources()
    reference = parse(ref)

    if explicit_source:
        require_installed(explicit_source, "--source names")
        if reference.source and reference.source != explicit_source:
            raise TicketError(
                f"'{ref}' names source '{reference.source}' but --source says '{explicit_source}'",
                EXIT_ERROR,
            )
        reference.source = explicit_source

    # Before any lookup: an id is joined onto directories, and only one its
    # source's pattern admits can name a ticket directory rather than another.
    if reference.source:
        validate_id(reference.source, reference.id)

    scope = narrow(restrict, reference.product, ref)
    found = find_existing(reference, scope, context, ref)
    if found:
        return Target(
            found,
            filed=True,
            address=reference.coordinates,
            outside_context=bool(context and not context.contains(found.product)),
        )

    if reference.source is None:
        reference.source = default_source_for(scope, context)

    validate_id(reference.source, reference.id)
    choice = filing.choose(
        reference.source,
        restrict=scope,
        address=reference.coordinates,
        context=context,
        cwd=cwd,
    )
    return Target(
        Location(choice.product, reference.source, reference.id),
        filed=False,
        filing=choice,
        address=reference.coordinates,
        outside_context=bool(context and not context.contains(choice.product)),
    )


def ticket_coordinates(
    location: Location, record: dict, address: dict | None = None
) -> dict:
    """
    What locates this ticket upstream: the product's binding, overridden by the ticket's own.

    A ticket's recorded coordinates win because they are its identity, while a
    binding is only where new tickets are fetched from by default.
    """
    merged = config.binding(
        location.source, location.product.namespace, location.product.name
    )
    merged.update(record.get("coordinates") or {})
    merged.update(address or {})
    return merged


def is_usable(source: str, coordinates: dict) -> bool:
    return all(coordinates.get(name) for name in providers.coordinates(source))


def provider_context(
    source: str,
    product: Product | None,
    location: Location | None = None,
    coordinates: dict | None = None,
) -> dict:
    """
    What every provider entry point is handed, so none rebuilds it.

    A provider reads its coordinates from here and nowhere else. It never
    opens a config file or builds a ticket path itself, which is what lets one
    source be bound in any number of products.
    """
    namespace, name = (product.namespace, product.name) if product else (None, None)
    merged = config.effective(namespace, name)[0]
    binding = config.binding(source, namespace, name)
    ctx = {
        "source": source,
        "id": location.id if location else "",
        "manifest": providers.load_manifest(source),
        "product": product.ref if product else None,
        "config": merged,
        "binding": binding,
        "coordinates": coordinates if coordinates is not None else binding,
        "provider_dir": str(providers.provider_dir(source)),
        "tickets_home": str(paths.tickets_home()),
    }
    if location:
        ctx["location"] = location
        ctx["ticket_dir"] = str(location.dir)
        ctx["paths"] = location.paths()
    return ctx


def describe_source(source: str) -> dict:
    """The source-level half of the resolver output, with no ticket resolved."""
    manifest = providers.load_manifest(source)
    return {
        "source": source,
        "kind": manifest.get("kind"),
        "nouns": manifest.get("nouns") or {},
        "formats": manifest.get("formats") or {},
        "capabilities": manifest.get("capabilities") or {},
        "coordinate_levels": providers.coordinates(source),
        "role_files": providers.role_files(source),
        "provider_dir": str(providers.provider_dir(source)),
        "types_dir": str(providers.types_root()),
        "known_types": providers.list_types(),
    }


def describe_scope(scope: Scope | None) -> dict:
    namespace, product = (scope.namespace, scope.product) if scope else (None, None)
    merged, origins = config.effective(namespace, product)
    return {"config": config.redact(merged), "config_sources": origins}


def resolve(
    ref: str | None,
    explicit_source: str | None = None,
    type_override: str | None = None,
    require: list[str] | None = None,
    restrict: Scope | None = None,
    context: Scope | None = None,
    cwd: Path | None = None,
) -> dict:
    """The full resolver output — every path absolute, every secret redacted."""
    if ref is None:
        require_sources()
        source = explicit_source or default_source_for(restrict, context)
        require_installed(
            source, "--source names" if explicit_source else "default_source is"
        )
        resolved = describe_source(source)
        resolved.update({"id": None, "scope": restrict.ref if restrict else None})
        resolved.update(describe_scope(restrict))
        resolved["paths"] = {"tickets_home": str(paths.tickets_home())}
        return resolved

    target = locate(ref, explicit_source, restrict, context, cwd)
    location = target.location
    record = tickets.load(location)

    if type_override:
        known = providers.list_types()
        if known and type_override not in known:
            raise TicketError(
                f"unknown ticket type '{type_override}'",
                EXIT_ERROR,
                "Known types: " + ", ".join(known) + ".",
            )
        if location.dir.is_dir():
            record = tickets.update(location, type=type_override)
        else:
            record = {**record, "type": type_override}

    coordinates = ticket_coordinates(location, record, target.address)
    survey = tickets.on_disk(location, is_usable(location.source, coordinates))
    merged, origins = config.effective(
        location.product.namespace, location.product.name
    )

    resolved = describe_source(location.source)
    resolved.update(
        {
            "id": location.id,
            "ref": location.ref,
            "qualified_ref": location.qualified,
            "namespace": location.product.namespace,
            "product": location.product.ref,
            "filed": target.filed,
            "filing": target.filing.as_dict() if target.filing else None,
            "context": context.ref if context else None,
            "outside_context": target.outside_context,
            "type": record.get("type"),
            "native_type": record.get("native_type"),
            "title": record.get("title"),
            "state": record.get("state"),
            "url": record.get("url"),
            "last_fetched_at": record.get("last_fetched_at"),
            "type_file": type_file_for(record.get("type")),
            "coordinates": coordinates,
            "paths": location.paths(),
            "ticket_json": record,
            "config": config.redact(merged),
            "config_sources": origins,
            "on_disk": survey,
        }
    )

    unmet = [name for name in (require or []) if not survey.get(name)]
    if unmet:
        raise TicketError(
            f"{location.qualified} is missing " + ", ".join(unmet),
            EXIT_REQUIRE_UNMET,
            requirement_hint(location, unmet),
        )

    return resolved


def type_file_for(ticket_type: str | None) -> str | None:
    if not ticket_type:
        return None
    path = providers.types_root() / f"{ticket_type}.md"
    return str(path) if path.is_file() else None


def requirement_hint(location: Location, unmet: list[str]) -> str:
    """
    Name the skill that would satisfy each unmet requirement.

    Which skill that is depends on the source: a store that cannot fetch is
    populated by `/ticket-new`, and pointing it at `/ticket-fetch` would send
    the user to a verb that structurally refuses.
    """
    source = location.source
    ref = location.qualified
    populate = (
        f"Run `/ticket-fetch {ref}`."
        if providers.has_capability(source, "fetch")
        else f"Run `/ticket-new` to create it — `{source}` has no fetch."
    )
    steps = {
        "config": f"Run `/ticket-setup {source} --in {location.product.ref}` to bind it there.",
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
