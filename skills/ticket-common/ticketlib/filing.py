#!/usr/bin/env python3
"""
Choosing the product a ticket not yet on disk is filed under.

Two steps, in this order:

1. **Which products can hold it.** A product named with `--in` or a qualified
   reference, alone. A pasted address, the product bound to its coordinates —
   or, where only the namespace is, that namespace's `default` product — and
   nothing further applies. Otherwise every product whose bindings give the
   source every coordinate it needs; for a source that needs none, every product.
   A product bound to different coordinates than the ticket's is never one.
2. **Which of those is preferred**, when more than one can: the session
   context, then a product or namespace whose own scan roots hold the
   invocation directory, then the default product. When none of them decides,
   the caller is told to ask.

Preferences never widen step 1. That is what keeps a default from filing a
work item under a product bound to a different project, however convenient
the default is.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from . import config, layout, paths, providers
from .errors import EXIT_AMBIGUOUS, EXIT_ERROR, TicketError
from .layout import Location, Product, Scope


@dataclass(frozen=True)
class Filing:
    product: Product
    rule: str
    reason: str

    def as_dict(self) -> dict:
        return {"product": self.product.ref, "rule": self.rule, "reason": self.reason}


def same(left: object, right: object) -> bool:
    return str(left).casefold() == str(right).casefold()


def describe(coordinates: dict) -> str:
    return ", ".join(f"{name} '{value}'" for name, value in coordinates.items())


def conflicts(binding: dict, coordinates: dict) -> dict[str, tuple[str, str]]:
    """Each coordinate both sides name but disagree on, as (bound, given)."""
    return {
        name: (str(binding[name]), str(value))
        for name, value in coordinates.items()
        if binding.get(name) and value and not same(binding[name], value)
    }


def can_hold(product: Product, source: str, coordinates: dict) -> bool:
    binding = config.binding(source, product.namespace, product.name)
    if conflicts(binding, coordinates):
        return False
    return all(
        binding.get(name) or coordinates.get(name)
        for name in providers.coordinates(source)
    )


def choose(
    source: str,
    *,
    restrict: Scope | None = None,
    address: dict | None = None,
    context: Scope | None = None,
    cwd: Path | None = None,
) -> Filing:
    address = address or {}

    # A scope that names nothing on disk is a typo, and filing into it would
    # quietly create the misspelled namespace or product.
    if restrict:
        layout.require_exists(restrict, "--in")
    if context:
        layout.require_exists(context, "the session context")

    named = restrict.as_product() if restrict else None
    if named:
        require_holds(named, source, address)
        return Filing(named, "named", f"named explicitly as {named.ref}")

    if address:
        return by_address(source, address, restrict)

    candidates = sorted(
        product
        for product in pool(restrict, context)
        if (restrict is None or restrict.contains(product))
        and can_hold(product, source, {})
    )

    if not candidates:
        where = f" in {restrict.ref}" if restrict else ""
        raise TicketError(
            f"'{source}' is not bound in any product{where}",
            EXIT_ERROR,
            f"Run `/ticket-setup {source}` to bind it, naming the product with --in.",
        )

    if len(candidates) == 1:
        return Filing(
            candidates[0],
            "only-candidate",
            f"the only product a ticket from {source} can be filed under",
        )

    if context:
        chosen = preferred_in(Scope(context.namespace, context.product), candidates)
        if chosen:
            return Filing(chosen, "context", f"the session context is {context.ref}")

    chosen, root = by_invocation_directory(candidates, cwd)
    if chosen:
        return Filing(
            chosen,
            "invocation-directory",
            f"the invocation directory is inside its scan root {root}",
        )

    namespace = restrict.namespace if restrict else config.default_namespace()
    for product in (
        Product(namespace, config.default_product(namespace)),
        Product(namespace, paths.DEFAULT_NAME),
    ):
        if product in candidates:
            return Filing(product, "default", f"the default product of {namespace}")

    raise TicketError(
        f"more than one product can hold this {source} ticket, and nothing prefers one",
        EXIT_AMBIGUOUS,
        "Name one with --in:\n"
        + "\n".join(f"  {product.ref}" for product in candidates),
    )


def require_holds(product: Product, source: str, coordinates: dict) -> None:
    binding = config.binding(source, product.namespace, product.name)
    mismatch = conflicts(binding, coordinates)
    if mismatch:
        detail = "; ".join(
            f"{name} is '{bound}' there, '{given}' here"
            for name, (bound, given) in mismatch.items()
        )
        raise TicketError(
            f"{product.ref} is bound to other {source} coordinates — {detail}",
            EXIT_ERROR,
            "A ticket is never filed against its own coordinates. Name a product bound to them, "
            "or that namespace's `default` product.",
        )

    missing = [
        name
        for name in providers.coordinates(source)
        if not (binding.get(name) or coordinates.get(name))
    ]
    if missing:
        raise TicketError(
            f"{product.ref} has no {source} {', '.join(missing)} to fetch from",
            EXIT_ERROR,
            f"Run `/ticket-setup {source} --in {product.ref}` to bind it.",
        )


def by_address(source: str, address: dict, restrict: Scope | None) -> Filing:
    exact = [
        product
        for product in layout.products()
        if (restrict is None or restrict.contains(product))
        and not product.is_default
        and binds_exactly(product, source, address)
    ]
    if len(exact) == 1:
        return Filing(exact[0], "address", f"it is bound to {describe(address)}")
    if len(exact) > 1:
        raise duplicate_binding(source, address, exact)

    at_namespace, at_product = providers.split_by_level(source, address)
    namespaces = [
        namespace
        for namespace in layout.namespaces()
        if at_namespace
        and namespace != paths.DEFAULT_NAME
        and (restrict is None or restrict.namespace == namespace)
        and binds_exactly_at(namespace, source, at_namespace)
    ]
    if len(namespaces) == 1:
        fallback = Product(namespaces[0], paths.DEFAULT_NAME)
        return Filing(
            fallback,
            "address",
            f"{namespaces[0]} is bound to {describe(at_namespace)}, "
            f"but no product in it to {describe(at_product)}",
        )
    if len(namespaces) > 1:
        raise duplicate_binding(
            source, at_namespace, [Product(name, "*") for name in namespaces]
        )

    raise TicketError(
        f"no namespace or product is bound to {source} {describe(address)}",
        EXIT_ERROR,
        f"Run `/ticket-setup {source}` with those coordinates to bind them.",
    )


def misfiling(location: Location, coordinates: dict) -> dict | None:
    """
    How a ticket's own coordinates contradict the product it is filed under, if they do.

    A ticket is filed before it is fetched, and only the fetch learns where it
    lives — an Azure DevOps id names no project — so this is the one filing
    that can only be checked after the fact. The product its coordinates do
    belong to is proposed alongside, when one is bound.
    """
    binding = config.binding(
        location.source, location.product.namespace, location.product.name
    )
    mismatch = conflicts(binding, coordinates)
    if not mismatch:
        return None

    try:
        belongs = by_address(location.source, coordinates, None).product.ref
    except TicketError:
        belongs = None

    return {
        "coordinates": {
            name: {"bound": bound, "ticket": own}
            for name, (bound, own) in mismatch.items()
        },
        "belongs_under": belongs,
    }


def binds_exactly(product: Product, source: str, coordinates: dict) -> bool:
    binding = config.binding(source, product.namespace, product.name)
    return all(
        binding.get(name) and same(binding[name], value)
        for name, value in coordinates.items()
    )


def binds_exactly_at(namespace: str, source: str, coordinates: dict) -> bool:
    binding = config.binding(source, namespace, None)
    return all(
        binding.get(name) and same(binding[name], value)
        for name, value in coordinates.items()
    )


def duplicate_binding(
    source: str, coordinates: dict, holders: list[Product]
) -> TicketError:
    return TicketError(
        f"{source} {describe(coordinates)} is bound in more than one place",
        EXIT_AMBIGUOUS,
        "A binding belongs to one namespace or product. Remove it from all but one of:\n"
        + "\n".join(f"  {product.ref}" for product in holders),
    )


def pool(restrict: Scope | None, context: Scope | None) -> set[Product]:
    """
    Every product on disk, plus the default products a preference could name.

    Those may not exist yet: a `default` product is created the first time a
    ticket lands in it, so it has to be a candidate before it is a directory.
    """
    found = set(layout.products())
    namespaces = {config.default_namespace(), paths.DEFAULT_NAME}
    for scope in (restrict, context):
        if scope:
            namespaces.add(scope.namespace)
    for namespace in namespaces:
        found.add(Product(namespace, config.default_product(namespace)))
        found.add(Product(namespace, paths.DEFAULT_NAME))
    return found


def preferred_in(scope: Scope, candidates: list[Product]) -> Product | None:
    """The candidate a scope points at, falling back to its namespace's default product."""
    named = scope.as_product()
    if named:
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
    candidates: list[Product], cwd: Path | None
) -> tuple[Product | None, str | None]:
    """
    A product, or else a namespace, whose own scan roots hold the invocation directory.

    Only a level's own scan roots count. An inherited list says where the
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
        return preferred_in(Scope(namespace), candidates), root

    return None, None


def holding_root(roots: list[str] | None, cwd: Path) -> str | None:
    here = os.path.normcase(str(cwd.resolve()))
    for root in roots or []:
        base = os.path.normcase(str(Path(root).expanduser().resolve()))
        if here == base or here.startswith(base.rstrip("\\/") + os.sep):
            return root
    return None
