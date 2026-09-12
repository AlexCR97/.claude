#!/usr/bin/env python3
"""
Reading and writing the two config levels.

Root `config.json` holds exactly one key, `default_source`. Everything a source
needs to connect — coordinates, a cached credential — lives in that source's
own `config.json`, so one source's setup can never disturb another's.
"""

import json
import os
from pathlib import Path

from . import paths


def read_json(path: Path) -> dict:
    """An absent or unreadable file reads as empty."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict) -> None:
    """Atomic write: a crash cannot leave a config half-written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def load_root() -> dict:
    return read_json(paths.root_config_path())


def save_root(config: dict) -> None:
    write_json(paths.root_config_path(), config)


def set_default_source(source: str) -> None:
    """Records the default without clobbering any other key already there."""
    config = load_root()
    config["default_source"] = source
    save_root(config)


def default_source() -> str | None:
    value = load_root().get("default_source")
    return str(value) if value else None


def load_source(source: str) -> dict:
    return read_json(paths.source_config_path(source))


def save_source(source: str, config: dict) -> None:
    write_json(paths.source_config_path(source), config)


def is_initialized(source: str) -> bool:
    return paths.source_config_path(source).exists()


def redact(config: dict) -> dict:
    """
    A config as it may be printed.

    `token` is replaced by its status rather than omitted, so a driver can tell
    "no credential yet" from "a credential that expired" without ever holding
    the secret.
    """
    from . import tokencache

    safe = dict(config)
    if "token" in safe:
        safe["token"] = tokencache.describe(safe["token"])
    return safe
