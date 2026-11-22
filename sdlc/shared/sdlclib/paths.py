"""Every path the plugin uses, absolute, built from names rather than found by walking the tree."""

import os
from pathlib import Path

HOME_ENV_VAR = "SDLC_HOME"

# The fallback namespace and product that receive a ticket nothing else claims.
DEFAULT_NAME = "default"


def sdlc_home() -> Path:
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".sdlc"


def ticket_dir(namespace: str, product: str, source: str, ticket_id: str) -> Path:
    return sdlc_home() / namespace / product / source / ticket_id


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
