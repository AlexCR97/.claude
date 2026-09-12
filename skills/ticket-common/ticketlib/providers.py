#!/usr/bin/env python3
"""
Discovering and loading the provider directories.

This is the single function that knows the tree layout. Sources are found by
glob, never by a hardcoded list, so adding one is adding a directory.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from .errors import EXIT_ERROR, EXIT_NO_CAPABILITY, TicketError

MANIFEST_NAME = "provider.json"
MODULE_NAME = "provider.py"

# Role files every source must have — they answer a question that has no
# source-independent answer, so a missing one is a gap, never a default.
REQUIRED_ROLE_FILES = ("config.md", "schema.md", "types.md", "links.md")

# A capability is claimed in provider.json and documented in a role file. The
# two must agree: `ticket.py sources --check` is what enforces it.
CAPABILITY_ROLE_FILES = {
    "fetch": "fetch.md",
    "new": "new.md",
    "publish": "publish.md",
    "drift": "drift.md",
}


def providers_root() -> Path:
    # ticketlib/ -> ticket-common/ -> skills/ -> ticket-providers/
    return Path(__file__).resolve().parent.parent.parent / "ticket-providers"


def types_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "ticket-types"


def list_sources() -> list[str]:
    root = providers_root()
    if not root.is_dir():
        return []
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and (entry / MANIFEST_NAME).is_file()
    )


def list_types() -> list[str]:
    root = types_root()
    if not root.is_dir():
        return []
    return sorted(
        entry.stem
        for entry in root.glob("*.md")
        if entry.name.lower() != "readme.md"
    )


def provider_dir(source: str) -> Path:
    return providers_root() / source


def load_manifest(source: str) -> dict:
    path = provider_dir(source) / MANIFEST_NAME
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TicketError(
            f"unknown source '{source}' — no {path}",
            EXIT_ERROR,
            f"Known sources: {', '.join(list_sources()) or 'none'}.",
        ) from exc
    except (json.JSONDecodeError, OSError) as exc:
        raise TicketError(f"could not read {path} — {exc}") from exc

    if not isinstance(manifest, dict):
        raise TicketError(f"{path} is not a JSON object")

    manifest.setdefault("source", source)
    return manifest


def role_files(source: str) -> list[str]:
    directory = provider_dir(source)
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.glob("*.md"))


def role_file(source: str, name: str) -> str | None:
    """The absolute path of a role file, or None when this source lacks it."""
    path = provider_dir(source) / name
    return str(path) if path.is_file() else None


def capabilities(source: str) -> dict:
    raw = load_manifest(source).get("capabilities")
    return raw if isinstance(raw, dict) else {}


def has_capability(source: str, name: str) -> bool:
    return bool(capabilities(source).get(name))


def require_capability(source: str, name: str) -> None:
    """
    Gate a verb on a declared capability, before any module is loaded.

    Refusing here rather than inside the module is what makes an absent
    capability structural: there is no code path for a driver to improvise past.
    """
    if has_capability(source, name):
        return

    manifest = load_manifest(source)
    noun = (manifest.get("nouns") or {}).get("singular", "ticket")
    raise TicketError(
        f"source '{source}' does not support '{name}'",
        EXIT_NO_CAPABILITY,
        f"Its provider.json declares capabilities.{name} = false, and there is "
        f"no {CAPABILITY_ROLE_FILES.get(name, name + '.md')} describing how a "
        f"{noun} would do it. This is a gap to report, not one to work around.",
    )


def load_module(source: str) -> ModuleType:
    """
    Import a source's provider.py by path.

    Namespacing on the source name is what lets two providers each have a
    private `_fetch.py` without colliding in sys.modules.
    """
    path = provider_dir(source) / MODULE_NAME
    if not path.is_file():
        raise TicketError(f"source '{source}' has no {MODULE_NAME}")

    module_name = f"ticket_provider_{source}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise TicketError(f"could not load {path}")

    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_private(source: str, name: str) -> ModuleType:
    """
    Load one of a provider's private `_name.py` modules.

    Namespaced on the source for the same reason `load_module` is: two
    providers may each have a `_fetch.py`, and neither may shadow the other.
    """
    import sys

    module_name = f"ticket_provider_{source}_{name.lstrip('_')}"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached

    path = provider_dir(source) / f"{name}.py"
    if not path.is_file():
        raise TicketError(f"source '{source}' has no {name}.py")

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise TicketError(f"could not load {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check() -> tuple[list[dict], list[str]]:
    """Validate that every manifest's capabilities match its role files."""
    report: list[dict] = []
    problems: list[str] = []

    for source in list_sources():
        manifest = load_manifest(source)
        present = set(role_files(source))
        declared = manifest.get("capabilities") or {}

        for capability, filename in CAPABILITY_ROLE_FILES.items():
            claimed = bool(declared.get(capability))
            documented = filename in present
            if claimed and not documented:
                problems.append(
                    f"{source}: capabilities.{capability} is true but {filename} is missing"
                )
            elif documented and not claimed:
                problems.append(
                    f"{source}: {filename} exists but capabilities.{capability} is not true"
                )

        for filename in REQUIRED_ROLE_FILES:
            if filename not in present:
                problems.append(f"{source}: required role file {filename} is missing")

        if not (provider_dir(source) / MODULE_NAME).is_file():
            problems.append(f"{source}: {MODULE_NAME} is missing")

        report.append(
            {
                "source": source,
                "kind": manifest.get("kind"),
                "prefixes": manifest.get("prefixes") or [],
                "nouns": manifest.get("nouns") or {},
                "formats": manifest.get("formats") or {},
                "capabilities": declared,
                "role_files": sorted(present),
            }
        )

    return report, problems
