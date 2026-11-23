"""
The shape of the SDLC home: namespaces, the products inside them, and the
ticket directories inside those.

Every name is a lowercase slug, which is what lets one directory mean the same
thing on a case-insensitive Windows disk as on a case-sensitive one. A
provider's own spelling (`Billing.App`) lives in a binding, never in a
directory name. A name starting with a dot is never a namespace or a product.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .errors import SdlcError

NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")


@dataclass(frozen=True, order=True)
class Product:
    namespace: str
    name: str

    @property
    def ref(self) -> str:
        return f"{self.namespace}/{self.name}"

    @property
    def dir(self) -> Path:
        return paths.product_dir(self.namespace, self.name)

    @property
    def is_fallback(self) -> bool:
        return self.name == paths.DEFAULT_NAME


@dataclass(frozen=True, order=True)
class TicketDirectory:
    product: Product
    source: str
    id: str

    @property
    def ref(self) -> str:
        return f"{self.source}:{self.id}"

    @property
    def qualified(self) -> str:
        return f"{self.product.ref}/{self.ref}"

    @property
    def dir(self) -> Path:
        return paths.ticket_dir(
            self.product.namespace, self.product.name, self.source, self.id
        )


@dataclass(frozen=True)
class Scope:
    """A namespace, or one product in it: what the session context prefers."""

    namespace: str
    product: str | None = None

    @property
    def ref(self) -> str:
        return f"{self.namespace}/{self.product}" if self.product else self.namespace

    def contains(self, product: Product) -> bool:
        if product.namespace != self.namespace:
            return False
        return self.product is None or product.name == self.product


def is_name(name: str) -> bool:
    return bool(NAME_PATTERN.fullmatch(name))


def require_name(name: str, what: str) -> str:
    if not is_name(name):
        raise SdlcError(
            f"'{name}' is not a valid {what} name",
            hint="Names are lowercase letters, digits and hyphens, starting with a letter or digit.",
        )
    return name


def parse_scope(text: str) -> Scope:
    """`{namespace}` or `{namespace}/{product}`."""
    parts = text.strip().strip("/").split("/")
    if len(parts) > 2 or not parts[0]:
        raise SdlcError(
            f"'{text}' is not a namespace or a {{namespace}}/{{product}}",
            hint="Pass `acme` or `acme/billing-app`.",
        )
    namespace = require_name(parts[0], "namespace")
    product = require_name(parts[1], "product") if len(parts) == 2 else None
    return Scope(namespace, product)


def require_exists(scope: Scope, what: str) -> None:
    """
    Refuse a scope naming a namespace or product that is not on disk.

    Filing into it would quietly create a misspelled one. The `default`
    namespace and every `default` product are the exception: they are created
    the first time a ticket lands in them.
    """
    missing = None
    if (
        scope.namespace != paths.DEFAULT_NAME
        and not paths.namespace_dir(scope.namespace).is_dir()
    ):
        missing = f"namespace '{scope.namespace}'"
    elif (
        scope.product
        and scope.product != paths.DEFAULT_NAME
        and not paths.product_dir(scope.namespace, scope.product).is_dir()
    ):
        missing = f"product '{scope.ref}'"
    if missing:
        raise SdlcError(
            f"{what} names {missing}, which does not exist",
            hint=f"Create it with `/sdlc:setup`, or check the spelling of {scope.ref}.",
        )


def parse_context(text: str | None) -> Scope | None:
    """The session context, which must name something on disk; None when none was given."""
    if not text:
        return None
    context = parse_scope(text)
    require_exists(context, "the session context")
    return context


def namespaces() -> list[str]:
    home = paths.sdlc_home()
    if not home.is_dir():
        return []
    return sorted(
        entry.name for entry in home.iterdir() if entry.is_dir() and is_name(entry.name)
    )


def products(namespace: str | None = None) -> list[Product]:
    found: list[Product] = []
    for name in [namespace] if namespace else namespaces():
        directory = paths.namespace_dir(name)
        if not directory.is_dir():
            continue
        found.extend(
            Product(name, entry.name)
            for entry in sorted(directory.iterdir())
            if entry.is_dir() and is_name(entry.name)
        )
    return found


def tickets(product: Product) -> list[TicketDirectory]:
    """Every ticket directory filed under a product, by source then id."""
    return [
        TicketDirectory(product, source.name, entry.name)
        for source in sorted(product.dir.iterdir())
        if source.is_dir()
        for entry in sorted(source.iterdir())
        if entry.is_dir()
    ]


def ticket_directories(
    sources: list[str], ticket_id: str, product: Product | None = None
) -> list[TicketDirectory]:
    """Every directory on disk holding this id under one of the sources, optionally in one product."""
    return [
        TicketDirectory(candidate, source, ticket_id)
        for candidate in ([product] if product else products())
        for source in sources
        if (candidate.dir / source / ticket_id).is_dir()
    ]


def nearest(
    matches: list[TicketDirectory], prefer: Scope | None
) -> list[TicketDirectory]:
    """
    The matches in the closest tier: the preferred product, its namespace, then everywhere.

    Only the closest non-empty tier is returned, so a caller sees ambiguity
    exactly when two matches are equally close, never when a nearer one exists.
    """
    if not prefer or len(matches) < 2:
        return matches

    tiers = []
    if prefer.product:
        tiers.append([match for match in matches if prefer.contains(match.product)])
    tiers.append(
        [match for match in matches if match.product.namespace == prefer.namespace]
    )
    for tier in tiers:
        if tier:
            return tier
    return matches
