#!/usr/bin/env python3
"""
Reading, merging and writing the three config levels.

The tickets home, each namespace and each product may hold a `config.json`.
Every skill reads the effective config — the three merged, the inner level
winning — so a product records only what differs from its namespace, and a
namespace only what differs from the machine. Objects merge key by key, which
is how a namespace's `sources.ado.organization` and a product's
`sources.ado.project` combine into one binding; anything else replaces what
an outer level set, so `scan_roots: []` clears an inherited list.

A key describing a level's relationship to what is inside it is read from that
level alone and never merged: `layout` and `default_namespace` belong to the
root, `default_product` to a namespace. A product inheriting `default_product`
would be naming a product that is not there.

No credential lives in any of these files. They are hand-edited and merged,
and a token inherited or overridden by accident is a token printed by
accident, so `tokencache` keeps credentials in a store of their own.
"""

import json
import os
from pathlib import Path

from . import paths

LEVEL_ONLY_KEYS = frozenset({"layout", "default_namespace", "default_product"})


def read_json(path: Path) -> dict:
    """An absent or unreadable file reads as empty."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict, mode: int | None = None) -> None:
    """
    Atomic write: a crash cannot leave a config half-written.

    With `mode`, the file is created with those permissions rather than
    narrowed to them afterwards, so a credential is never readable by anyone
    else even for the moment between the write and a chmod.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if mode is None:
        temp_path.write_text(text, encoding="utf-8")
    else:
        temp_path.unlink(missing_ok=True)
        descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
    os.replace(temp_path, path)


def load_level(namespace: str | None = None, product: str | None = None) -> dict:
    return read_json(paths.level_config_path(namespace, product))


def update_level(
    changes: dict, namespace: str | None = None, product: str | None = None
) -> dict:
    """
    Set top-level keys without clobbering the rest of the file.

    A key passed as None is removed rather than written as null: every key in
    these files is optional, and an absent key is what "inherit it" means.
    """
    data = load_level(namespace, product)
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    write_json(paths.level_config_path(namespace, product), data)
    return data


def load_root() -> dict:
    return load_level()


def save_root(data: dict) -> None:
    write_json(paths.root_config_path(), data)


def level_paths(namespace: str | None, product: str | None) -> list[Path]:
    """The config files that apply, outermost first."""
    levels = [paths.root_config_path()]
    if namespace is not None:
        levels.append(paths.level_config_path(namespace))
        if product is not None:
            levels.append(paths.level_config_path(namespace, product))
    return levels


def effective(
    namespace: str | None = None, product: str | None = None
) -> tuple[dict, dict[str, str]]:
    """
    The merged config, and which file each of its values came from.

    The second half is what answers "why did this plan scan that directory?":
    each leaf is keyed by its dotted path — `scan_roots`,
    `sources.ado.project` — and maps to the absolute path of the file that set it.
    """
    merged: dict = {}
    origins: dict[str, str] = {}
    for path in level_paths(namespace, product):
        layer = {
            key: value
            for key, value in read_json(path).items()
            if key not in LEVEL_ONLY_KEYS
        }
        merge_into(merged, layer, str(path), origins, "")
    return merged, origins


def merge_into(
    target: dict, layer: dict, origin: str, origins: dict, prefix: str
) -> None:
    for key, value in layer.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_into(target[key], value, origin, origins, f"{dotted}.")
            continue

        # A replaced value takes every origin at and beneath it along with it.
        for stale in [
            name for name in origins if name == dotted or name.startswith(f"{dotted}.")
        ]:
            del origins[stale]

        if isinstance(value, dict):
            target[key] = {}
            merge_into(target[key], value, origin, origins, f"{dotted}.")
        else:
            target[key] = value
            origins[dotted] = origin


def binding(source: str, namespace: str | None, product: str | None) -> dict:
    """The coordinates this level inherits and sets for one source."""
    sources = effective(namespace, product)[0].get("sources")
    value = sources.get(source) if isinstance(sources, dict) else None
    return dict(value) if isinstance(value, dict) else {}


def own_binding(source: str, namespace: str | None, product: str | None = None) -> dict:
    """The coordinates this one level's file sets for a source, inherited ones excluded."""
    sources = load_level(namespace, product).get("sources")
    value = sources.get(source) if isinstance(sources, dict) else None
    return dict(value) if isinstance(value, dict) else {}


def set_binding(
    source: str, coordinates: dict, namespace: str, product: str | None = None
) -> None:
    """Merge coordinates into one level's `sources.{source}`, leaving every other key alone."""
    if not coordinates:
        return
    data = load_level(namespace, product)
    sources = data.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    entry = sources.get(source)
    if not isinstance(entry, dict):
        entry = {}
    entry.update(coordinates)
    sources[source] = entry
    data["sources"] = sources
    write_json(paths.level_config_path(namespace, product), data)


def default_source(
    namespace: str | None = None, product: str | None = None
) -> str | None:
    value = effective(namespace, product)[0].get("default_source")
    return str(value) if value else None


def set_default_source(source: str) -> None:
    update_level({"default_source": source})


def scan_roots(
    namespace: str | None = None, product: str | None = None
) -> tuple[list[str], str | None]:
    """The effective scan roots, and the file that set them — None when none did."""
    merged, origins = effective(namespace, product)
    value = merged.get("scan_roots")
    if not isinstance(value, list):
        return [], None
    return [str(path) for path in value], origins.get("scan_roots")


def own_scan_roots(
    namespace: str | None = None, product: str | None = None
) -> list[str] | None:
    """What this one level sets, or None when it inherits."""
    value = load_level(namespace, product).get("scan_roots")
    return [str(path) for path in value] if isinstance(value, list) else None


def set_scan_roots(
    directories: list[str], namespace: str | None = None, product: str | None = None
) -> None:
    update_level({"scan_roots": directories}, namespace, product)


def default_namespace() -> str:
    value = load_level().get("default_namespace")
    return str(value) if value else paths.DEFAULT_NAME


def default_product(namespace: str) -> str:
    value = load_level(namespace).get("default_product")
    return str(value) if value else paths.DEFAULT_NAME


def redact(config: dict) -> dict:
    """
    A config as it may be printed.

    No level should hold a `token` any more, but one written by hand or left by
    an older layout is still replaced by its status rather than shown.
    """
    from . import tokencache

    safe = dict(config)
    if "token" in safe:
        safe["token"] = tokencache.describe(safe["token"])
    return safe
