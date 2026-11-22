"""
`fetch`: mirror a ticket from its source into the ticket's `raw/` directory.

The ticket is found, or filed, by the same logic `resolve` uses, so a ticket's
own coordinates win over any binding and a first fetch lands under the bound
product. The source's fetcher writes `raw/` and returns the fields the source
determines; this module records them in `ticket.json` and leaves every other
key alone, which is how a `type` the model recorded survives a refresh.

Nothing is written when the source cannot be read: a half-mirrored ticket
would read as a complete one.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from . import config as configuration
from . import providers, resolve
from .errors import SdlcError

FETCHED_FIELDS = ("title", "state", "url", "fingerprint")


def read_record(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise SdlcError(f"{path}: is not a valid ticket record ({error})") from error
    if not isinstance(record, dict):
        raise SdlcError(f"{path}: must hold a JSON object")
    return record


def write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_suffix(".json.tmp")
    scratch.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(scratch, path)


def fetch(
    reference_text: str,
    coordinate_arguments: list[str],
    context_text: str | None,
    cwd: Path,
) -> dict:
    config = configuration.load()
    context = resolve.parse_context(context_text)
    found = resolve.locate_existing(
        config,
        resolve.parse_reference(reference_text),
        coordinate_arguments,
        context,
        cwd,
    )
    location = found.location

    if not providers.load_manifest(location.source)["capabilities"]["fetch"]:
        raise SdlcError(
            f"{location.ref} is a {location.source} ticket, which has no upstream to fetch from"
        )

    coordinates = {**resolve.ticket_coordinates(config, location), **found.coordinates}
    missing = [
        name
        for name in providers.coordinates(location.source)
        if name not in coordinates
    ]
    if missing:
        raise SdlcError(
            f"{location.product.ref} has no {location.source} {', '.join(missing)} to fetch from",
            hint="Bind them with `/sdlc:setup`, or name them with --coordinate.",
        )

    mirrored = providers.load_fetcher(location.source).fetch(
        location.id, coordinates, location.dir / "raw"
    )

    record_path = location.dir / "ticket.json"
    record = read_record(record_path)
    record.update(source=location.source, id=location.id, coordinates=coordinates)
    record.update({field: mirrored[field] for field in FETCHED_FIELDS})
    record["last_fetched_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    write_record(record_path, record)

    return {
        **resolve.report(
            config,
            location,
            exists=found.exists,
            context=context,
            chosen=found.chosen,
        ),
        "fetched": mirrored["report"],
    }
