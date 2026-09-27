#!/usr/bin/env python3
"""
The shape of the tickets home: namespaces, the products inside them, and the
ticket directories inside those.

Every name is a lowercase slug. That is what lets one directory mean the same
thing on a case-insensitive Windows disk as on a case-sensitive one, and it is
why a provider's own spelling — `EW.Educate` — lives in a binding rather than
in a directory name. A name starting with a dot is never a namespace or a
product: the credential store is one, and so is an editor's `.obsidian`.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import paths, providers
from .errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError

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
    def is_default(self) -> bool:
        return self.name == paths.DEFAULT_NAME


@dataclass(frozen=True, order=True)
class Location:
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

    def paths(self) -> dict[str, str]:
        return paths.ticket_paths(
            self.product.namespace, self.product.name, self.source, self.id
        )

    def ref_from(self, product: Product) -> str:
        """
        How a ticket filed under `product` writes a reference to this one.

        Short within the same product, qualified across products — the same
        rule that resolves a stored reference nearest-first, so what is written
        here always resolves back to this ticket.
        """
        return self.ref if product == self.product else self.qualified


@dataclass(frozen=True)
class Scope:
    """A namespace, or one product in it: what `--in` restricts to and `--context` prefers."""

    namespace: str
    product: str | None = None

    @property
    def ref(self) -> str:
        return f"{self.namespace}/{self.product}" if self.product else self.namespace

    def contains(self, product: Product) -> bool:
        if product.namespace != self.namespace:
            return False
        return self.product is None or product.name == self.product

    def as_product(self) -> Product | None:
        return Product(self.namespace, self.product) if self.product else None

    @staticmethod
    def of(product: Product) -> "Scope":
        return Scope(product.namespace, product.name)


def is_name(name: str) -> bool:
    return bool(NAME_PATTERN.fullmatch(name))


def require_name(name: str, what: str) -> str:
    if not is_name(name):
        raise TicketError(
            f"'{name}' is not a valid {what} name",
            EXIT_ERROR,
            "Names are lowercase letters, digits and hyphens, starting with a letter or digit.",
        )
    return name


def parse_scope(text: str) -> Scope:
    """`{namespace}` or `{namespace}/{product}`."""
    parts = text.strip().strip("/").split("/")
    if len(parts) > 2 or not parts[0]:
        raise TicketError(
            f"'{text}' is not a namespace or a {{namespace}}/{{product}}",
            EXIT_ERROR,
            "Pass `edwire` or `edwire/ew-educate`.",
        )
    namespace = require_name(parts[0], "namespace")
    product = require_name(parts[1], "product") if len(parts) == 2 else None
    return Scope(namespace, product)


def parse_product(text: str) -> Product:
    scope = parse_scope(text)
    product = scope.as_product()
    if product is None:
        raise TicketError(
            f"'{text}' names a namespace, not a product",
            EXIT_ERROR,
            f"Pass `{scope.namespace}/{{product}}`.",
        )
    return product


def require_exists(scope: Scope, what: str) -> None:
    """
    Refuse a scope naming a namespace or product that is not on disk.

    The `default` namespace and every `default` product are the exceptions:
    they are created the first time a ticket lands in them, so their not
    existing yet is expected rather than a typo.
    """
    if (
        scope.namespace != paths.DEFAULT_NAME
        and not paths.namespace_dir(scope.namespace).is_dir()
    ):
        raise TicketError(
            f"{what} names namespace '{scope.namespace}', which does not exist",
            EXIT_NOT_FOUND,
            f"Create it with `/ticket-init --in {scope.ref}`, or check the spelling.",
        )
    if (
        scope.product
        and scope.product != paths.DEFAULT_NAME
        and not paths.product_dir(scope.namespace, scope.product).is_dir()
    ):
        raise TicketError(
            f"{what} names product '{scope.ref}', which does not exist",
            EXIT_NOT_FOUND,
            f"Create it with `/ticket-init --in {scope.ref}`, or check the spelling.",
        )


def slugify(text: str, fallback: str = paths.DEFAULT_NAME) -> str:
    """A directory name proposed from an upstream name: `EW.Educate` → `ew-educate`."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return slug or fallback


def namespaces() -> list[str]:
    home = paths.tickets_home()
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


def locations(
    source: str | None = None,
    ticket_id: str | None = None,
    scope: Scope | None = None,
) -> list[Location]:
    """Every ticket directory on disk, optionally narrowed to one source, id or scope."""
    if ticket_id is not None and not paths.is_segment(ticket_id):
        return []

    installed = providers.list_sources()
    sources = [source] if source else installed
    found: list[Location] = []

    for product in products(scope.namespace if scope else None):
        if scope and not scope.contains(product):
            continue
        for name in sources:
            if name not in installed:
                continue
            source_path = product.dir / name
            if not source_path.is_dir():
                continue
            if ticket_id is not None:
                if (source_path / ticket_id).is_dir():
                    found.append(Location(product, name, ticket_id))
                continue
            found.extend(
                Location(product, name, entry.name)
                for entry in sorted(source_path.iterdir())
                if entry.is_dir()
            )

    return found


def nearest(matches: list[Location], prefer: Scope | None) -> list[Location]:
    """
    The matches in the closest tier: the preferred product, its namespace, then everywhere.

    Only the closest non-empty tier is returned, so a caller sees ambiguity
    exactly when two matches are equally close — never when a nearer one exists.
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
