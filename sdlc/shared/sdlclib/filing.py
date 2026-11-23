"""
Choosing the product a ticket not yet on disk is filed under.

Two steps, in this order:

1. Which products can hold it: a named product alone; or, for explicit
   coordinates, the product bound to them; otherwise every product whose
   bindings give the source every coordinate it needs (every product, for a
   source that needs none). A product bound to other coordinates than the
   ticket's is never one.
2. Which of those is preferred: the session context, then a product or
   namespace whose own scan roots hold the invocation directory, then the
   default product. When none decides, the caller is told to ask.

Preferences never widen step 1, which is what keeps a default from filing a
work item under a product bound to a different project.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from . import paths, providers
from .config import Config, describe, same
from .errors import EXIT_AMBIGUOUS, SdlcError
from .layout import Product, Scope, namespaces, products, require_exists


class FilingReport(TypedDict):
    product: str
    rule: str
    reason: str


@dataclass(frozen=True)
class Filing:
    product: Product
    rule: str
    reason: str

    def as_dict(self) -> FilingReport:
        return {"product": self.product.ref, "rule": self.rule, "reason": self.reason}


def conflicts(binding: dict, coordinates: dict) -> dict[str, tuple[str, str]]:
    """Each coordinate both sides name but disagree on, as (bound, given)."""
    return {
        name: (str(binding[name]), str(value))
        for name, value in coordinates.items()
        if binding.get(name) and value and not same(binding[name], value)
    }


def can_hold(config: Config, product: Product, source: str) -> bool:
    binding = config.binding(source, product)
    return all(name in binding for name in providers.coordinates(source))


def choose(
    config: Config,
    source: str,
    *,
    named: Product | None = None,
    coordinates: dict | None = None,
    context: Scope | None = None,
    cwd: Path | None = None,
) -> Filing:
    coordinates = coordinates or {}

    if named:
        require_exists(Scope(named.namespace, named.name), "the reference")
        require_holds(config, named, source, coordinates)
        return Filing(named, "named", f"named explicitly as {named.ref}")

    if coordinates:
        return by_coordinates(config, source, coordinates)

    candidates = sorted(
        product
        for product in pool(config, context)
        if can_hold(config, product, source)
    )
    if not candidates:
        raise SdlcError(
            f"'{source}' is not bound in any product",
            hint=f"Run `/sdlc:setup` to bind {source}, naming the namespace and product.",
        )

    if len(candidates) == 1:
        return Filing(
            candidates[0],
            "only-candidate",
            f"the only product a {source} ticket can be filed under",
        )

    if context:
        chosen = preferred_in(config, context, candidates)
        if chosen:
            return Filing(chosen, "context", f"the session context is {context.ref}")

    chosen, root = by_invocation_directory(config, candidates, cwd)
    if chosen:
        return Filing(
            chosen,
            "invocation-directory",
            f"the invocation directory is inside its scan root {root}",
        )

    namespace = config.default_namespace()
    for product in (
        Product(namespace, config.default_product(namespace)),
        Product(namespace, paths.DEFAULT_NAME),
    ):
        if product in candidates:
            return Filing(product, "default", f"the default product of {namespace}")

    raise SdlcError(
        f"more than one product can hold this {source} ticket, and nothing prefers one",
        EXIT_AMBIGUOUS,
        "Name one with a qualified reference:\n"
        + "\n".join(f"  {product.ref}" for product in candidates),
    )


def require_holds(
    config: Config, product: Product, source: str, coordinates: dict
) -> None:
    binding = config.binding(source, product)
    mismatch = conflicts(binding, coordinates)
    if mismatch:
        detail = "; ".join(
            f"{name} is '{bound}' there, '{given}' here"
            for name, (bound, given) in mismatch.items()
        )
        raise SdlcError(
            f"{product.ref} is bound to other {source} coordinates: {detail}",
            hint="A ticket is never filed against its own coordinates. Name a product bound "
            "to them, or that namespace's `default` product.",
        )

    missing = [
        name
        for name in providers.coordinates(source)
        if name not in binding and name not in coordinates
    ]
    if missing:
        raise SdlcError(
            f"{product.ref} has no {source} {', '.join(missing)} to fetch from",
            hint=f"Run `/sdlc:setup` to bind {source} under {product.ref}.",
        )


def by_coordinates(config: Config, source: str, coordinates: dict) -> Filing:
    at_namespace, at_product = providers.split_by_level(source, coordinates)

    exact = [
        product
        for product in products()
        if at_product
        and not product.is_fallback
        and binds_all(config.binding(source, product), coordinates)
    ]
    if len(exact) == 1:
        return Filing(
            exact[0], "coordinates", f"it is bound to {describe(coordinates)}"
        )
    if exact:
        raise SdlcError(
            f"{source} {describe(coordinates)} is bound in more than one product",
            EXIT_AMBIGUOUS,
            "Name one with a qualified reference:\n"
            + "\n".join(f"  {product.ref}" for product in exact),
        )

    matching = [
        namespace
        for namespace in namespaces()
        if at_namespace
        and namespace != paths.DEFAULT_NAME
        and binds_all(config.namespace_binding(source, namespace), at_namespace)
    ]
    if matching:
        return Filing(
            Product(matching[0], paths.DEFAULT_NAME),
            "coordinates",
            f"{matching[0]} is bound to {describe(at_namespace)}, "
            f"but no product in it to {describe(at_product)}",
        )

    raise SdlcError(
        f"no namespace or product is bound to {source} {describe(coordinates)}",
        hint="Run `/sdlc:setup` with those coordinates to bind them.",
    )


def binds_all(binding: dict, coordinates: dict) -> bool:
    return all(
        name in binding and same(binding[name], value)
        for name, value in coordinates.items()
    )


def pool(config: Config, context: Scope | None) -> set[Product]:
    """
    Every product on disk, plus the default products a preference could name.

    Those may not exist yet: a fallback product is created the first time a
    ticket lands in it, so it has to be a candidate before it is a directory.
    """
    found = set(products())
    scopes = {config.default_namespace(), paths.DEFAULT_NAME}
    if context:
        scopes.add(context.namespace)
    for namespace in scopes:
        found.add(Product(namespace, config.default_product(namespace)))
        found.add(Product(namespace, paths.DEFAULT_NAME))
    return found


def preferred_in(
    config: Config, scope: Scope, candidates: list[Product]
) -> Product | None:
    """The candidate a scope points at, falling back to its namespace's default product."""
    if scope.product:
        named = Product(scope.namespace, scope.product)
        return named if named in candidates else None

    in_namespace = [
        product for product in candidates if product.namespace == scope.namespace
    ]
    if len(in_namespace) == 1:
        return in_namespace[0]

    for product in (
        Product(scope.namespace, config.default_product(scope.namespace)),
        Product(scope.namespace, paths.DEFAULT_NAME),
    ):
        if product in candidates:
            return product
    return None


def by_invocation_directory(
    config: Config, candidates: list[Product], cwd: Path | None
) -> tuple[Product | None, str | None]:
    """
    A product, or else a namespace, whose own scan roots hold the invocation directory.

    Only a level's own scan roots count: an inherited list says where the
    machine keeps code, not which product this directory belongs to.
    """
    if cwd is None:
        return None, None

    hits = [
        (product, root)
        for product in candidates
        for root in [
            holding_root(config.own_scan_roots(product.namespace, product.name), cwd)
        ]
        if root
    ]
    if len(hits) == 1:
        return hits[0]

    by_namespace: dict[str, str] = {}
    for namespace in sorted({product.namespace for product in candidates}):
        root = holding_root(config.own_scan_roots(namespace), cwd)
        if root:
            by_namespace[namespace] = root
    if len(by_namespace) == 1:
        namespace, root = next(iter(by_namespace.items()))
        return preferred_in(config, Scope(namespace), candidates), root

    return None, None


def holding_root(roots: list[str] | None, cwd: Path) -> str | None:
    here = os.path.normcase(str(cwd.resolve()))
    for root in roots or []:
        base = os.path.normcase(str(Path(root).expanduser().resolve()))
        if here == base or here.startswith(base.rstrip("\\/") + os.sep):
            return root
    return None
