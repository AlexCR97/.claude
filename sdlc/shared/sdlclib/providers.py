"""A source's flat manifest, shipped beside the code as `providers/{source}.json`."""

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

from .errors import SdlcError

PROVIDERS_DIR = Path(__file__).resolve().parent.parent / "providers"

# A coordinate is bound at one of the two levels that hold a binding; the
# manifest says which, so an organization and a repository land in the right file.
COORDINATE_LEVELS = ("namespace", "product")


def list_sources() -> list[str]:
    return sorted(path.stem for path in PROVIDERS_DIR.glob("*.json"))


def load_manifest(source: str) -> dict:
    path = PROVIDERS_DIR / f"{source}.json"
    if not path.is_file():
        raise SdlcError(
            f"source '{source}' is not available",
            hint="Available sources: " + ", ".join(list_sources()) + ".",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def source_for_prefix(prefix: str) -> str | None:
    for source in list_sources():
        if prefix in load_manifest(source)["prefixes"]:
            return source
    return None


def coordinates(source: str) -> dict[str, str]:
    """Each coordinate the source declares, mapped to the level it is bound at."""
    return dict(load_manifest(source)["coordinates"])


def split_by_level(source: str, values: dict) -> tuple[dict, dict]:
    """Coordinates as (namespace-level, product-level)."""
    levels = coordinates(source)
    return (
        {name: value for name, value in values.items() if levels[name] == "namespace"},
        {name: value for name, value in values.items() if levels[name] == "product"},
    )


def id_fits(source: str, ticket_id: str) -> bool:
    return bool(re.fullmatch(load_manifest(source)["id"]["pattern"], ticket_id))


def load_fetcher(source: str) -> ModuleType:
    """The source's `providers/{source}.py`, which exposes `fetch(ticket_id, coordinates, raw_dir)` and `check(ticket_id, coordinates)`."""
    path = PROVIDERS_DIR / f"{source}.py"
    if not path.is_file():
        raise SdlcError(f"source '{source}' has no fetcher")
    spec = importlib.util.spec_from_file_location(f"sdlc_provider_{source}", path)
    if spec is None or spec.loader is None:
        raise SdlcError(f"source '{source}' has a fetcher that cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
