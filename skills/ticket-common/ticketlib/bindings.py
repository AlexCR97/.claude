#!/usr/bin/env python3
"""
Where a source's binding is filed, whether it may be, and writing it.

A binding is split across two files by the level each coordinate belongs to —
an organization on the namespace, a project on the product — so a second
product in a bound namespace inherits the first half and records only its own.

A fallback product receives what no binding fits, so it is never bound: the
`default` namespace holds no namespace-level coordinate, and no `default`
product holds a product-level one.
"""

from . import config, filing, layout, paths, providers, sources
from .layout import Product


def levels(source: str, product: Product, coordinates: dict) -> tuple[dict, dict]:
    """The (namespace-level, product-level) halves `product` may hold, fallback levels emptied."""
    at_namespace, at_product = providers.split_by_level(source, coordinates)
    if product.namespace == paths.DEFAULT_NAME:
        at_namespace = {}
    if product.is_default:
        at_product = {}
    return at_namespace, at_product


def write(source: str, product: Product, coordinates: dict) -> None:
    at_namespace, at_product = levels(source, product, coordinates)
    config.set_binding(source, at_namespace, product.namespace)
    config.set_binding(source, at_product, product.namespace, product.name)


def derive(source: str, coordinates: dict) -> Product:
    """Names derived from the coordinates themselves: `edwire` and `EW.Educate` → `edwire/ew-educate`."""
    at_namespace, at_product = providers.split_by_level(source, coordinates)
    if not at_namespace:
        return Product(paths.DEFAULT_NAME, paths.DEFAULT_NAME)
    return Product(
        layout.slugify(str(next(iter(at_namespace.values())))),
        layout.slugify(str(next(iter(at_product.values()))))
        if at_product
        else paths.DEFAULT_NAME,
    )


def propose(source: str, coordinates: dict) -> Product:
    """
    Where a binding would be filed when no `--in` names a place.

    Its own product when one already has exactly this binding — a
    re-initialization — else a new product in the namespace already bound to
    its namespace-level coordinates, else names derived from the coordinates.
    """
    if not coordinates:
        return Product(paths.DEFAULT_NAME, paths.DEFAULT_NAME)

    for product in layout.products():
        if not product.is_default and filing.binds_exactly(
            product, source, coordinates
        ):
            return product

    derived = derive(source, coordinates)
    at_namespace, _ = providers.split_by_level(source, coordinates)
    bound = next(
        (
            name
            for name in layout.namespaces()
            if name != paths.DEFAULT_NAME
            and at_namespace
            and filing.binds_exactly_at(name, source, at_namespace)
        ),
        None,
    )
    return Product(bound or derived.namespace, derived.name)


def problems(source: str, product: Product, coordinates: dict) -> list[str]:
    """Everything that would make binding these coordinates under `product` file some address wrongly."""
    at_namespace, at_product = providers.split_by_level(source, coordinates)
    found = []

    if product.namespace == paths.DEFAULT_NAME and at_namespace:
        found.append(
            "the `default` namespace receives tickets no namespace fits, so it cannot be "
            f"bound to {source} {filing.describe(at_namespace)} — name another namespace with --in"
        )
    if product.is_default and at_product:
        found.append(
            "a namespace's `default` product receives tickets no product fits, so it cannot be "
            f"bound to {source} {filing.describe(at_product)} — name another product with --in"
        )

    for level_binding, given, where in (
        (
            config.binding(source, product.namespace, None),
            at_namespace,
            f"namespace {product.namespace}",
        ),
        (
            config.own_binding(source, product.namespace, product.name),
            at_product,
            product.ref,
        ),
    ):
        for name, (bound, wanted) in filing.conflicts(level_binding, given).items():
            found.append(
                f"{where} is already bound to {source} {name} '{bound}', not '{wanted}' — "
                "edit its config.json to repoint it, or bind this elsewhere"
            )

    # A source that declares no coordinates has nothing to duplicate.
    complete = bool(coordinates) and sources.is_usable(source, coordinates)
    for other in layout.products():
        if (
            other != product
            and complete
            and filing.binds_exactly(other, source, coordinates)
        ):
            found.append(
                f"{source} {filing.describe(coordinates)} is already bound under {other.ref}"
            )
    for namespace in layout.namespaces():
        if (
            namespace != product.namespace
            and at_namespace
            and filing.binds_exactly_at(namespace, source, at_namespace)
        ):
            found.append(
                f"{source} {filing.describe(at_namespace)} is already bound to namespace {namespace}"
            )

    for name, what in ((product.namespace, "namespace"), (product.name, "product")):
        if not layout.is_name(name):
            found.append(f"'{name}' is not a valid {what} name")

    return found
