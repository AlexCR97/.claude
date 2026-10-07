#!/usr/bin/env python3
"""
Every path the suite uses, resolved absolutely in one place.

Absolute is not a detail: a driver hands these straight to a file tool or a
quoted shell argument, neither of which expands `~`.

A ticket directory always sits at the same depth,
`{namespace}/{product}/{source}/{id}`, so every path here is built from names
rather than found by walking the tree.
"""

import os
import re
from pathlib import Path

# Overriding the tickets home lets a test run against a scratch tree without touching
# the real one.
HOME_ENV_VAR = "TICKETS_HOME"

# The six entries a ticket directory may hold; anything else is a stray.
TICKET_ENTRIES = (
    "ticket.json",
    "digest.md",
    "journal.md",
    "plan.md",
    "raw",
    "artifacts",
)

CONFIG_FILENAME = "config.json"

# Reserved as both a namespace and a product name: every namespace's `default`
# product receives a ticket whose namespace is known but that no product fits,
# and `default/default` one that no namespace fits either.
DEFAULT_NAME = "default"

# A leading dot keeps it from ever reading as a namespace.
CREDENTIALS_DIRNAME = ".credentials"

CREDENTIAL_KEY_UNSAFE = re.compile(r"[^a-z0-9._-]+")


def tickets_home() -> Path:
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".tickets"


def root_config_path() -> Path:
    return tickets_home() / CONFIG_FILENAME


def namespace_dir(namespace: str) -> Path:
    return tickets_home() / namespace


def product_dir(namespace: str, product: str) -> Path:
    return namespace_dir(namespace) / product


def level_config_path(namespace: str | None = None, product: str | None = None) -> Path:
    """The root's config with no names, a namespace's with one, a product's with both."""
    if namespace is None:
        return root_config_path()
    if product is None:
        return namespace_dir(namespace) / CONFIG_FILENAME
    return product_dir(namespace, product) / CONFIG_FILENAME


def credentials_path(source: str, key: str) -> Path:
    """
    Where one credential is cached, keyed by the coordinate it was issued for.

    The key is lowercased and made filename-safe because it is an upstream
    name — an organization, an account — and those are case-insensitive and
    may hold characters a filename cannot.
    """
    safe_key = CREDENTIAL_KEY_UNSAFE.sub("_", key.casefold()).strip("._") or "_"
    return tickets_home() / CREDENTIALS_DIRNAME / source / f"{safe_key}.json"


def is_segment(name: str) -> bool:
    """
    Whether a name is exactly one path component.

    A ticket id is joined onto a directory, so an id that is `..` or holds a
    separator would name a directory above or beside the one it belongs in —
    a namespace, say, which a move would then rename.
    """
    return (
        bool(name) and name not in (".", "..") and not any(c in name for c in "/\\\0")
    )


def ticket_dir(namespace: str, product: str, source: str, ticket_id: str) -> Path:
    return product_dir(namespace, product) / source / ticket_id


def ticket_paths(
    namespace: str, product: str, source: str, ticket_id: str
) -> dict[str, str]:
    """Every path a driver may need, absolute, whether or not it exists yet."""
    root = ticket_dir(namespace, product, source, ticket_id)
    return {
        "tickets_home": str(tickets_home()),
        "namespace_dir": str(namespace_dir(namespace)),
        "namespace_config": str(level_config_path(namespace)),
        "product_dir": str(product_dir(namespace, product)),
        "product_config": str(level_config_path(namespace, product)),
        "source_dir": str(product_dir(namespace, product) / source),
        "ticket_dir": str(root),
        "ticket_json": str(root / "ticket.json"),
        "digest": str(root / "digest.md"),
        "plan": str(root / "plan.md"),
        "journal": str(root / "journal.md"),
        "raw_dir": str(root / "raw"),
        "artifacts_dir": str(root / "artifacts"),
    }
