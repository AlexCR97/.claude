"""
`resolve`: where a ticket lives, or where a new one would be filed. Read-only.

The skill writes the ticket's files at the reported paths; nothing here creates
a directory, so a report can be asked for as often as needed.
"""

import re

from . import paths, providers
from .errors import SdlcError

# A title longer than this makes an unwieldy directory name.
MAX_SLUG_WORDS = 8

LOCAL = "local"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(slug.split("-")[:MAX_SLUG_WORDS])


def parse_reference(reference: str) -> tuple[str, str]:
    """Split `[source:]id` into a source and an id the source accepts."""
    prefix, separator, ticket_id = reference.rpartition(":")
    source = providers.source_for_prefix(prefix) if separator else LOCAL
    if source is None:
        raise SdlcError(
            f"'{reference}' names a source that is not available",
            hint="Available sources: " + ", ".join(providers.list_sources()) + ".",
        )
    pattern = providers.load_manifest(source)["id"]["pattern"]
    if not re.fullmatch(pattern, ticket_id):
        raise SdlcError(
            f"'{ticket_id}' is not a valid {source} ticket id",
            hint=f"A {source} id looks like: {providers.load_manifest(source)['id']['shape']}.",
        )
    return source, ticket_id


def report(source: str, ticket_id: str) -> dict:
    ticket_paths = paths.ticket_paths(
        paths.DEFAULT_NAME, paths.DEFAULT_NAME, source, ticket_id
    )
    return {
        "source": source,
        "id": ticket_id,
        "ref": f"{source}:{ticket_id}",
        "namespace": paths.DEFAULT_NAME,
        "product": f"{paths.DEFAULT_NAME}/{paths.DEFAULT_NAME}",
        "exists": paths.ticket_dir(
            paths.DEFAULT_NAME, paths.DEFAULT_NAME, source, ticket_id
        ).is_dir(),
        "paths": ticket_paths,
    }


def resolve(reference: str | None, new: bool, title: str | None) -> dict:
    if new:
        if reference or not title:
            raise SdlcError("--new takes a --title and no reference")
        ticket_id = slugify(title)
        if not ticket_id:
            raise SdlcError(
                f"the title '{title}' has no letters or digits to name a ticket after"
            )
        found = report(LOCAL, ticket_id)
        if found["exists"]:
            raise SdlcError(
                f"{found['ref']} already exists",
                hint="Choose a different title, or resolve it as an existing ticket.",
            )
        return found

    if not reference:
        raise SdlcError("resolve takes a reference, or --new --title")
    return report(*parse_reference(reference))
