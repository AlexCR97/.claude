#!/usr/bin/env python3
"""
Every path the suite uses, resolved absolutely in one place.

Absolute is not a detail: a driver hands these straight to a file tool or a
quoted shell argument, neither of which expands `~`.
"""

import os
from pathlib import Path

# Overriding the root lets a test run against a scratch tree without touching
# the real one.
HOME_ENV_VAR = "TICKETS_HOME"

# The six entries a ticket root may hold; anything else is a stray.
TICKET_ENTRIES = ("ticket.json", "digest.md", "journal.md", "plan.md", "raw", "artifacts")


def tickets_home() -> Path:
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".tickets"


def legacy_home() -> Path:
    """The pre-`~/.tickets` layout, read only to detect that a migration is due."""
    return Path.home() / ".az-workitems"


def root_config_path() -> Path:
    return tickets_home() / "config.json"


def source_dir(source: str) -> Path:
    return tickets_home() / source


def source_config_path(source: str) -> Path:
    return source_dir(source) / "config.json"


def ticket_dir(source: str, ticket_id: str) -> Path:
    return source_dir(source) / ticket_id


def ticket_paths(source: str, ticket_id: str) -> dict[str, str]:
    """Every path a driver may need, absolute, whether or not it exists yet."""
    root = ticket_dir(source, ticket_id)
    return {
        "tickets_home": str(tickets_home()),
        "source_dir": str(source_dir(source)),
        "source_config": str(source_config_path(source)),
        "ticket_dir": str(root),
        "ticket_json": str(root / "ticket.json"),
        "digest": str(root / "digest.md"),
        "plan": str(root / "plan.md"),
        "journal": str(root / "journal.md"),
        "raw_dir": str(root / "raw"),
        "artifacts_dir": str(root / "artifacts"),
    }
