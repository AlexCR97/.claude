"""A source's flat manifest, shipped beside the code in `providers/{source}/provider.json`."""

import json
from pathlib import Path

from .errors import SdlcError

PROVIDERS_DIR = Path(__file__).resolve().parent.parent / "providers"


def list_sources() -> list[str]:
    return sorted(entry.parent.name for entry in PROVIDERS_DIR.glob("*/provider.json"))


def load_manifest(source: str) -> dict:
    path = PROVIDERS_DIR / source / "provider.json"
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
