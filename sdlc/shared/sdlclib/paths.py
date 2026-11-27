"""Every path the plugin uses, absolute, built from names rather than found by walking the tree."""

import os
from pathlib import Path

HOME_ENV_VAR = "SDLC_HOME"
CONNECTIONS_HOME_ENV_VAR = "SDLC_CONNECTIONS_HOME"

# The leading dot is what keeps the profiles out of namespace listing and export:
# `layout.is_name` never accepts a name that starts with one.
CONNECTIONS_DIR_NAME = ".connections"

# The fallback namespace and product that receive a ticket nothing else claims.
DEFAULT_NAME = "default"

ROOT_CONFIG_NAME = "sdlc.json"
NAMESPACE_CONFIG_NAME = "namespace.json"
PRODUCT_CONFIG_NAME = "product.json"


def sdlc_home() -> Path:
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".sdlc"


def connections_home() -> Path:
    override = os.environ.get(CONNECTIONS_HOME_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return sdlc_home() / CONNECTIONS_DIR_NAME


def root_config_path() -> Path:
    return sdlc_home() / ROOT_CONFIG_NAME


def namespace_dir(namespace: str) -> Path:
    return sdlc_home() / namespace


def namespace_config_path(namespace: str) -> Path:
    return namespace_dir(namespace) / NAMESPACE_CONFIG_NAME


def product_dir(namespace: str, product: str) -> Path:
    return namespace_dir(namespace) / product


def product_config_path(namespace: str, product: str) -> Path:
    return product_dir(namespace, product) / PRODUCT_CONFIG_NAME


def ticket_dir(namespace: str, product: str, source: str, ticket_id: str) -> Path:
    return product_dir(namespace, product) / source / ticket_id


def ticket_paths(
    namespace: str, product: str, source: str, ticket_id: str
) -> dict[str, str]:
    root = ticket_dir(namespace, product, source, ticket_id)
    return {
        "sdlc_home": str(sdlc_home()),
        "ticket_dir": str(root),
        "ticket_json": str(root / "ticket.json"),
        "ticket_file": str(root / "raw" / "ticket.md"),
    }
