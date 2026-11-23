"""
`archive export`: write the SDLC home, or one namespace, product or ticket of
it, to a zip that `archive import` on another machine reads back.

The format is `shared/archive.md`. Every entry is relative to the SDLC home
with forward slashes, so the same zip reads the same on Windows and elsewhere.
"""

import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from . import config as configuration
from . import layout, paths, resolve
from .errors import EXIT_AMBIGUOUS, SdlcError
from .layout import Product, TicketDirectory

MANIFEST_NAME = "manifest.json"
FORMAT_NAME = "sdlc-archive"
FORMAT_VERSION = 1


class ScopeRecord(TypedDict):
    kind: str
    ref: str | None


@dataclass(frozen=True)
class ExportScope:
    kind: str
    ref: str | None
    config_files: list[Path]
    directories: list[Path]
    tickets: list[TicketDirectory]

    def as_dict(self) -> ScopeRecord:
        return {"kind": self.kind, "ref": self.ref}


class Manifest(TypedDict):
    format: str
    version: int
    scope: ScopeRecord
    created_at: str
    source_home: str
    tickets: list[str]


class ExportReport(TypedDict):
    archive: str
    scope: ScopeRecord
    tickets: int
    created_at: str
    source_home: str


def tickets_of(products: list[Product]) -> list[TicketDirectory]:
    return [found for product in products for found in layout.tickets(product)]


def whole_home() -> ExportScope:
    return ExportScope(
        "home",
        None,
        [paths.root_config_path()],
        [paths.namespace_dir(name) for name in layout.namespaces()],
        tickets_of(layout.products()),
    )


def namespace(name: str) -> ExportScope:
    return ExportScope(
        "namespace",
        name,
        [paths.root_config_path()],
        [paths.namespace_dir(name)],
        tickets_of(layout.products(name)),
    )


def product(chosen: Product) -> ExportScope:
    return ExportScope(
        "product",
        chosen.ref,
        [
            paths.root_config_path(),
            paths.namespace_config_path(chosen.namespace),
        ],
        [chosen.dir],
        tickets_of([chosen]),
    )


def ticket(chosen: TicketDirectory) -> ExportScope:
    return ExportScope(
        "ticket",
        chosen.qualified,
        [
            paths.root_config_path(),
            paths.namespace_config_path(chosen.product.namespace),
            paths.product_config_path(chosen.product.namespace, chosen.product.name),
        ],
        [chosen.dir],
        [chosen],
    )


def ticket_on_disk(text: str, context_text: str | None) -> TicketDirectory | None:
    config = configuration.load()
    context = layout.parse_context(context_text)
    return resolve.find_on_disk(config, resolve.parse_reference(text), {}, context)


def find_ticket(text: str, context_text: str | None) -> TicketDirectory:
    found = ticket_on_disk(text, context_text)
    if not found:
        raise SdlcError(
            f"'{text}' names no namespace, product or ticket in the SDLC home",
            hint="Pass a namespace, `namespace/product`, or a ticket reference.",
        )
    return found


def namespace_or_ticket(name: str, context_text: str | None) -> ExportScope:
    """A bare name is a namespace when one exists, unless a ticket has the same id."""
    if not paths.namespace_dir(name).is_dir():
        return ticket(find_ticket(name, context_text))
    try:
        same_id = ticket_on_disk(name, context_text)
    except SdlcError as error:
        if error.code != EXIT_AMBIGUOUS:
            return namespace(name)
        raise ambiguous_name(name, error.hint.splitlines()[1:]) from error
    if same_id:
        raise ambiguous_name(name, [f"  {same_id.qualified}"])
    return namespace(name)


def ambiguous_name(name: str, ticket_lines: list[str]) -> SdlcError:
    return SdlcError(
        f"'{name}' names a namespace and a ticket",
        EXIT_AMBIGUOUS,
        "Pass the ticket's qualified reference, or `source:id`:\n"
        + "\n".join(ticket_lines),
    )


def parse_scope(text: str | None, context_text: str | None) -> ExportScope:
    if not text:
        if not paths.sdlc_home().is_dir():
            raise SdlcError(f"the SDLC home {paths.sdlc_home()} does not exist")
        return whole_home()
    segments = text.split("/")
    if len(segments) == 3 or ":" in text:
        return ticket(find_ticket(text, context_text))
    if len(segments) == 2:
        chosen = Product(
            layout.require_name(segments[0], "namespace"),
            layout.require_name(segments[1], "product"),
        )
        if not chosen.dir.is_dir():
            raise SdlcError(f"product '{chosen.ref}' is not in the SDLC home")
        return product(chosen)
    return namespace_or_ticket(layout.require_name(text, "namespace"), context_text)


def files_under(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*") if path.is_file())


def archive_path(scope: ExportScope, out: str | None, cwd: Path, now: datetime) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", (scope.ref or "home").lower()).strip("-")
    name = f"sdlc-{slug}-{now.strftime('%Y-%m-%dT%H-%M-%SZ')}.zip"
    target = (cwd / Path(out).expanduser()) if out else cwd
    if target.is_dir():
        target = target / name
    target = target.resolve()
    # The next export would carry this archive inside the one it writes.
    if target.is_relative_to(paths.sdlc_home()):
        raise SdlcError(
            f"{target} is inside the SDLC home",
            hint="Write the archive outside the SDLC home.",
        )
    if target.exists():
        raise SdlcError(
            f"{target} already exists",
            hint="Name another file with --out; an archive never overwrites one.",
        )
    return target


def write_zip(target: Path, home: Path, files: list[Path], manifest: Manifest) -> None:
    try:
        with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(home).as_posix())
            archive.writestr(MANIFEST_NAME, layout.json_bytes(manifest))
    except OSError as error:
        target.unlink(missing_ok=True)
        raise SdlcError(f"could not write {target} ({error})") from error


def export(
    scope_text: str | None, out: str | None, context_text: str | None, cwd: Path
) -> ExportReport:
    home = paths.sdlc_home()
    scope = parse_scope(scope_text, context_text)
    now = datetime.now(UTC).replace(microsecond=0)
    target = archive_path(scope, out, cwd, now)
    tickets = [found.qualified for found in scope.tickets]
    manifest: Manifest = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "scope": scope.as_dict(),
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_home": str(home),
        "tickets": tickets,
    }
    files = [path for path in scope.config_files if path.is_file()]
    for directory in scope.directories:
        files.extend(files_under(directory))
    write_zip(target, home, files, manifest)
    return {
        "archive": str(target),
        "scope": scope.as_dict(),
        "tickets": len(tickets),
        "created_at": manifest["created_at"],
        "source_home": manifest["source_home"],
    }
