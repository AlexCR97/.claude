"""
`resolve`: where a ticket lives, or where a new one would be filed. Read-only.

The skill writes the ticket's files at the reported paths; nothing here creates
a directory, so a report can be asked for as often as needed.

A reference is `[{namespace}/{product}/][{source}:]{id}`. An existing ticket is
found by the nearest level (the session context's product, its namespace, then
everywhere); two equally near is an error that lists them, since guessing would
attach work to the wrong ticket. A ticket on disk nowhere is filed by
`filing.py`. The session context only ever prefers: it never moves a ticket that
is already filed.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import config as configuration
from . import filing, layout, paths, providers
from .config import Config
from .errors import EXIT_AMBIGUOUS, SdlcError
from .layout import Location, Product, Scope

# A title longer than this makes an unwieldy directory name.
MAX_SLUG_WORDS = 8

LOCAL = "local"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(slug.split("-")[:MAX_SLUG_WORDS])


def available_sources_hint() -> str:
    return "Available sources: " + ", ".join(providers.list_sources()) + "."


@dataclass(frozen=True)
class Reference:
    id: str
    source: str | None
    named: Product | None


def parse_reference(text: str) -> Reference:
    segments = text.split("/")
    if len(segments) not in (1, 3):
        raise SdlcError(
            f"'{text}' is not a valid reference",
            hint="Write `[source:]id`, or `namespace/product/[source:]id`.",
        )
    named = None
    if len(segments) == 3:
        named = Product(
            layout.require_name(segments[0], "namespace"),
            layout.require_name(segments[1], "product"),
        )

    prefix, separator, ticket_id = segments[-1].rpartition(":")
    source = None
    if separator:
        source = providers.source_for_prefix(prefix)
        if source is None:
            raise SdlcError(
                f"'{text}' names a source that is not available",
                hint=available_sources_hint(),
            )
        validate_id(source, ticket_id)
    return Reference(ticket_id, source, named)


def validate_id(source: str, ticket_id: str) -> None:
    if not providers.id_fits(source, ticket_id):
        shape = providers.load_manifest(source)["id"]["shape"]
        raise SdlcError(
            f"'{ticket_id}' is not a valid {source} ticket id",
            hint=f"A {source} id looks like: {shape}.",
        )


def parse_coordinates(arguments: list[str], source: str | None) -> dict[str, str]:
    if not arguments:
        return {}
    if source is None:
        raise SdlcError(
            "--coordinate needs a reference that names its source",
            hint="Prefix the id, as in `ado:1234`.",
        )
    declared = providers.coordinates(source)
    coordinates: dict[str, str] = {}
    for argument in arguments:
        name, separator, value = argument.partition("=")
        if not separator or not value.strip():
            raise SdlcError(f"--coordinate '{argument}' is not name=value")
        if name not in declared:
            raise SdlcError(
                f"'{name}' is not a {source} coordinate",
                hint="Declared: " + (", ".join(declared) or "none") + ".",
            )
        coordinates[name] = value
    return coordinates


def ticket_coordinates(config: Config, location: Location) -> dict:
    """What locates a ticket upstream: its product's binding, overridden by the ticket's own record."""
    coordinates = config.binding(location.source, location.product)
    record = location.dir / "ticket.json"
    if record.is_file():
        try:
            own = json.loads(record.read_text(encoding="utf-8")).get("coordinates")
        except (json.JSONDecodeError, OSError, AttributeError) as error:
            raise SdlcError(
                f"{record}: is not a valid ticket record ({error})"
            ) from error
        if isinstance(own, dict):
            coordinates.update(own)
    return coordinates


def default_source_for(
    config: Config, named: Product | None, context: Scope | None
) -> str:
    """The effective `default_source` of the nearest scope that says where the ticket goes."""
    scopes = [
        (named.namespace, named.name) if named else None,
        (context.namespace, context.product) if context else None,
    ]
    namespace = config.default_namespace()
    scopes.append((namespace, config.default_product(namespace)))
    for scope in scopes:
        if scope and (source := config.default_source(*scope)):
            return source
    raise SdlcError(
        "the id names no source, it is on disk nowhere, and no default_source is configured",
        hint="Prefix the id with a source, or set `default_source` with `/sdlc:setup`. "
        + available_sources_hint(),
    )


def report(
    config: Config,
    location: Location,
    *,
    exists: bool,
    context: Scope | None,
    chosen: filing.Filing | None = None,
) -> dict:
    product = location.product
    found = {
        "source": location.source,
        "id": location.id,
        "ref": location.ref,
        "namespace": product.namespace,
        "product": product.ref,
        "exists": exists,
        "outside_context": bool(context and not context.contains(product)),
        "paths": paths.ticket_paths(
            product.namespace, product.name, location.source, location.id
        ),
        "config": config.effective(product.namespace, product.name),
    }
    if chosen:
        found["filing"] = chosen.as_dict()
    return found


def ambiguous(matches: list[Location]) -> SdlcError:
    return SdlcError(
        f"the reference matches {len(matches)} tickets equally near",
        EXIT_AMBIGUOUS,
        "Name one with a qualified reference:\n"
        + "\n".join(f"  {match.qualified}" for match in matches),
    )


def resolve_new(
    config: Config, title: str | None, context: Scope | None, cwd: Path
) -> dict:
    ticket_id = slugify(title or "")
    if not ticket_id:
        raise SdlcError(
            f"the title '{title}' has no letters or digits to name a ticket after"
        )
    chosen = filing.choose(config, LOCAL, context=context, cwd=cwd)
    location = Location(chosen.product, LOCAL, ticket_id)
    if location.dir.is_dir():
        raise SdlcError(
            f"{location.qualified} already exists",
            hint="Choose a different title, or resolve it as an existing ticket.",
        )
    return report(config, location, exists=False, context=context, chosen=chosen)


def resolve_existing(
    config: Config,
    reference: Reference,
    coordinate_arguments: list[str],
    context: Scope | None,
    cwd: Path,
) -> dict:
    coordinates = parse_coordinates(coordinate_arguments, reference.source)
    sources = (
        [reference.source]
        if reference.source
        else [s for s in providers.list_sources() if providers.id_fits(s, reference.id)]
    )
    if not sources:
        raise SdlcError(
            f"'{reference.id}' is not a valid ticket id for any source",
            hint=available_sources_hint(),
        )

    matches = [
        match
        for match in layout.locations(sources, reference.id, reference.named)
        if not filing.conflicts(ticket_coordinates(config, match), coordinates)
    ]
    matches = layout.nearest(matches, context)
    if len(matches) > 1:
        raise ambiguous(matches)
    if matches:
        return report(config, matches[0], exists=True, context=context)

    source = reference.source or default_source_for(config, reference.named, context)
    validate_id(source, reference.id)
    chosen = filing.choose(
        config,
        source,
        named=reference.named,
        address=coordinates,
        context=context,
        cwd=cwd,
    )
    location = Location(chosen.product, source, reference.id)
    return report(config, location, exists=False, context=context, chosen=chosen)


def resolve(
    reference: str | None,
    new: bool,
    title: str | None,
    context_text: str | None,
    coordinate_arguments: list[str],
    cwd: Path,
) -> dict:
    config = configuration.load()

    context = None
    if context_text:
        context = layout.parse_scope(context_text)
        layout.require_exists(context, "the session context")

    if new:
        if reference or not title or coordinate_arguments:
            raise SdlcError("--new takes a --title and no reference or coordinates")
        return resolve_new(config, title, context, cwd)

    if not reference:
        raise SdlcError("resolve takes a reference, or --new --title")
    return resolve_existing(
        config, parse_reference(reference), coordinate_arguments, context, cwd
    )
