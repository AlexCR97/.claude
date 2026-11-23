"""
`archive import`: merge an archive that `archive export` wrote into the SDLC home.

Without `apply` it only reports what the merge would do. The merge rules are in
`shared/archive.md`.
"""

import copy
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path, PurePosixPath
from typing import TypedDict, cast

from . import config, layout, paths, providers
from .archive import FORMAT_NAME, FORMAT_VERSION, MANIFEST_NAME, Manifest
from .errors import SdlcError
from .layout import Product, TicketDirectory


class KeptMine(TypedDict):
    path: str
    reason: str


KeptBoth = TypedDict("KeptBoth", {"path": str, "as": str})


class MirrorChoice(TypedDict):
    ticket: str
    mine: dict | None
    theirs: dict | None
    taken: bool


class KeyChange(TypedDict):
    path: str
    keys: list[str]


class MissingPaths(TypedDict):
    ticket: str
    paths: list[str]


class Conflict(TypedDict):
    ticket: str
    files: list[str]


class Summary(TypedDict):
    adds: list[str]
    new_tickets: list[str]
    kept_mine: list[KeptMine]
    kept_both: list[KeptBoth]
    mirrors: list[MirrorChoice]
    merges: list[KeyChange]
    not_imported: list[KeyChange]
    missing_workspace_paths: list[MissingPaths]
    conflicts: list[Conflict]


class ImportReport(Summary):
    digest: str


class ApplyReport(ImportReport):
    applied: bool


def read_archive(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            return {
                info.filename: archive.read(info)
                for info in archive.infolist()
                if not info.is_dir()
            }
    except (OSError, zipfile.BadZipFile) as error:
        raise SdlcError(f"{path} is not a readable zip ({error})") from error


def check_manifest(path: Path, entries: dict[str, bytes]) -> Manifest:
    if MANIFEST_NAME not in entries:
        raise SdlcError(f"{path} has no {MANIFEST_NAME}, so it is not an sdlc archive")
    manifest = layout.parse_json_object(
        f"{path}: {MANIFEST_NAME}", entries.pop(MANIFEST_NAME)
    )
    if manifest.get("format") != FORMAT_NAME:
        raise SdlcError(f"{path} is not an sdlc archive")
    if manifest.get("version") != FORMAT_VERSION:
        raise SdlcError(
            f"{path} is archive format version {manifest.get('version')}, "
            f"which this reader does not know (it reads version {FORMAT_VERSION})",
            hint="Update the sdlc plugin on this machine, then import again.",
        )
    # The time names the copy of a differing artifact, so it must be only a time.
    if not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", str(manifest.get("created_at"))
    ):
        raise SdlcError(f"{path}: the manifest's created_at is not a UTC time")
    return cast(Manifest, manifest)


def locate(name: str) -> tuple[TicketDirectory, str] | None:
    """The ticket an archive entry belongs to, and the entry's path inside its directory."""
    parts = name.split("/", 4)
    if len(parts) < 5 or parts[2] not in providers.list_sources():
        return None
    namespace, product, source, ticket_id, within = parts
    return TicketDirectory(Product(namespace, product), source, ticket_id), within


def in_layout(name: str) -> bool:
    """Whether an entry names a file inside a home; anything else could land outside it."""
    if "\\" in name or ":" in name or name.startswith("/"):
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if len(parts) == 1:
        return name == paths.ROOT_CONFIG_NAME
    if not all(layout.is_name(part) for part in parts[:-1][:2]):
        return False
    located = locate(name)
    return located is None or layout.is_name(located[0].id)


def load(archive_text: str, cwd: Path) -> tuple[Manifest, dict[str, bytes]]:
    path = (cwd / Path(archive_text).expanduser()).resolve()
    entries = read_archive(path)
    manifest = check_manifest(path, entries)
    outside = sorted(name for name in entries if not in_layout(name))
    if outside:
        raise SdlcError(
            f"{path} holds entries that are not a path in an SDLC home: "
            + ", ".join(outside),
            hint="Nothing was written. Import only an archive `archive export` wrote.",
        )
    return manifest, entries


@dataclass
class Write:
    path: str
    content: bytes
    is_new: bool


@dataclass
class Merge:
    """What importing the archive would do to the home, and the writes that do it."""

    home: Path
    entries: dict[str, bytes]
    created_at: str
    adds: list[str] = field(default_factory=list)
    new_tickets: list[str] = field(default_factory=list)
    kept_mine: list[KeptMine] = field(default_factory=list)
    kept_both: list[KeptBoth] = field(default_factory=list)
    mirrors: list[MirrorChoice] = field(default_factory=list)
    merges: list[KeyChange] = field(default_factory=list)
    not_imported: list[KeyChange] = field(default_factory=list)
    missing_workspace_paths: list[MissingPaths] = field(default_factory=list)
    conflicts: dict[str, list[str]] = field(default_factory=dict)
    writes: list[Write] = field(default_factory=list)
    theirs_writes: dict[str, list[Write]] = field(default_factory=dict)

    def mine(self, name: str) -> bytes | None:
        path = self.home / name
        return path.read_bytes() if path.is_file() else None

    def add(self, name: str, content: bytes | None = None) -> None:
        """Write a file this home lacks: the archive's entry, unless `content` is given."""
        self.adds.append(name)
        if content is None:
            content = self.entries[name]
        self.writes.append(Write(name, content, is_new=True))

    def add_ticket(self, ticket: TicketDirectory, names: list[str]) -> None:
        self.new_tickets.append(ticket.qualified)
        for name in names:
            self.add(name)

    def replace(self, name: str, content: bytes) -> None:
        self.writes.append(Write(name, content, is_new=False))

    def merge_keys(self, name: str, keys: list[str], content: bytes) -> None:
        self.merges.append({"path": name, "keys": keys})
        self.replace(name, content)

    def keep_mine(self, name: str, reason: str) -> None:
        self.kept_mine.append({"path": name, "reason": reason})

    def keep_both(self, name: str) -> None:
        """Write the archive's copy beside this home's under a name taken from the export time."""
        content = self.entries[name]
        path = PurePosixPath(name)
        stamp = self.created_at.replace(":", "-")
        for attempt in count(1):
            again = f"-{attempt}" if attempt > 1 else ""
            beside = str(
                path.with_name(f"{path.stem}.imported-{stamp}{again}{path.suffix}")
            )
            existing = self.mine(beside)
            if existing == content:
                return
            if existing is None and beside not in self.entries:
                break
        self.kept_both.append({"path": name, "as": beside})
        self.writes.append(Write(beside, content, is_new=True))

    def choose_mirror(
        self, ticket: TicketDirectory, *, theirs: dict, mine: dict, taken: bool
    ) -> None:
        self.mirrors.append(
            {
                "ticket": ticket.qualified,
                "mine": mine.get("fingerprint"),
                "theirs": theirs.get("fingerprint"),
                "taken": taken,
            }
        )

    def leave_out(self, name: str, keys: list[str]) -> None:
        self.not_imported.append({"path": name, "keys": keys})

    def conflict(self, ticket: TicketDirectory, file: str, theirs: Write) -> None:
        """Ask keep-mine or take-theirs for the ticket; `theirs` is written only on take-theirs."""
        self.conflicts.setdefault(ticket.qualified, []).append(file)
        self.theirs_writes.setdefault(ticket.qualified, []).append(theirs)

    def report_missing_paths(self, ticket: TicketDirectory, found: list[str]) -> None:
        self.missing_workspace_paths.append(
            {"ticket": ticket.qualified, "paths": found}
        )

    def summary(self) -> Summary:
        return {
            "adds": sorted(self.adds),
            "new_tickets": self.new_tickets,
            "kept_mine": sorted(
                self.kept_mine, key=lambda kept: (kept["path"], kept["reason"])
            ),
            "kept_both": self.kept_both,
            "mirrors": self.mirrors,
            "merges": self.merges,
            "not_imported": self.not_imported,
            "missing_workspace_paths": self.missing_workspace_paths,
            "conflicts": [
                {"ticket": ref, "files": files}
                for ref, files in sorted(self.conflicts.items())
            ],
        }

    def digest(self) -> str:
        """Changes when the report would, or when any file the merge reads or writes changes."""
        state = {
            name: [
                hashlib.sha256(content).hexdigest(),
                hashlib.sha256(mine).hexdigest() if (mine := self.mine(name)) else None,
            ]
            for name, content in sorted(self.entries.items())
        }
        # Missing workspace paths are left out: they change nothing the merge writes.
        planned = {**self.summary(), "missing_workspace_paths": None}
        text = json.dumps([planned, state], sort_keys=True)
        return hashlib.sha256(text.encode()).hexdigest()


ASKED_FILES = ("plan.md", "pulls.md")
RECORD = "ticket.json"
UNPOSTED = "unposted_journal"
JOURNAL_NAME = re.compile(r"\d{4}-\d\d-\d\dT\d\d-\d\d-\d\dZ\.md")
# The `ticket.json` keys `fetch` writes with the mirror, so they follow whichever mirror is kept.
MIRROR_KEYS = ("title", "state", "url", "fingerprint", "last_fetched_at", "coordinates")


def merge_file(merge: Merge, name: str) -> None:
    """A file outside every ticket directory: a differing one is kept beside this home's."""
    mine = merge.mine(name)
    if mine is None:
        merge.add(name)
    elif mine != merge.entries[name]:
        merge.keep_both(name)


def merge_ticket_file(
    merge: Merge, ticket: TicketDirectory, within: str, name: str, *, is_local: bool
) -> None:
    mine = merge.mine(name)
    if mine is None:
        merge.add(name)
    elif mine == merge.entries[name]:
        return
    elif within.startswith("journal/"):
        merge.keep_mine(name, "a journal entry of the same name is already here")
    elif within in ASKED_FILES or (is_local and within.startswith("raw/")):
        merge.conflict(ticket, within, Write(name, merge.entries[name], is_new=False))
    else:
        merge.keep_both(name)


def is_newer(theirs: dict, mine: dict) -> bool:
    their_print, my_print = theirs.get("fingerprint"), mine.get("fingerprint")
    if their_print == my_print:
        return False
    their_rev = (their_print or {}).get("rev")
    my_rev = (my_print or {}).get("rev")
    if isinstance(their_rev, int) and isinstance(my_rev, int):
        return their_rev > my_rev
    # A content hash has no order, so the later fetch is the later revision.
    return str(theirs.get("last_fetched_at") or "") > str(
        mine.get("last_fetched_at") or ""
    )


def merge_mirror(
    merge: Merge, ticket: TicketDirectory, raw: list[str], *, theirs: dict, mine: dict
) -> bool:
    """Take the archive's `raw/` whole when it is newer; returns whether it was taken."""
    if not any(merge.mine(name) is not None for name in raw):
        for name in raw:
            merge.add(name)
        return True
    differing = [name for name in raw if merge.mine(name) != merge.entries[name]]
    if not differing:
        return False
    taken = is_newer(theirs, mine)
    merge.choose_mirror(ticket, theirs=theirs, mine=mine, taken=taken)
    for name in differing if taken else []:
        if merge.mine(name) is None:
            merge.add(name)
        else:
            merge.replace(name, merge.entries[name])
    return taken


def merge_record(
    merge: Merge,
    ticket: TicketDirectory,
    files: dict[str, str],
    *,
    mirror_taken: bool,
) -> None:
    name = files[RECORD]
    mine_bytes = merge.mine(name)
    if mine_bytes is None:
        merge.add(name)
        return
    if mine_bytes == merge.entries[name]:
        return
    mine = layout.parse_json_object(name, mine_bytes)
    theirs = layout.parse_json_object(name, merge.entries[name])
    merged = dict(mine)
    if mirror_taken:
        merged.update({key: theirs[key] for key in MIRROR_KEYS if key in theirs})
    unposted = unposted_union(ticket, files, mine=mine, theirs=theirs)
    if unposted:
        merged[UNPOSTED] = unposted
    asked = []
    for key, value in theirs.items():
        if key in MIRROR_KEYS or key == UNPOSTED:
            continue
        if key not in mine:
            merged[key] = value
        elif mine[key] != value:
            asked.append(key)
    changed = sorted(key for key in merged if merged.get(key) != mine.get(key))
    if changed:
        merge.merge_keys(name, changed, layout.json_bytes(merged))
    if asked:
        taken = {**merged, **{key: theirs[key] for key in asked}}
        merge.conflict(
            ticket, RECORD, Write(name, layout.json_bytes(taken), is_new=False)
        )


def unposted_union(
    ticket: TicketDirectory, files: dict[str, str], *, mine: dict, theirs: dict
) -> list[str]:
    """Entries either home has not posted yet still wait; checkpoint skips one already posted."""
    names = {
        entry
        for record in (mine, theirs)
        if isinstance(record.get(UNPOSTED), list)
        for entry in record[UNPOSTED]
        if isinstance(entry, str) and JOURNAL_NAME.fullmatch(entry)
    }
    return sorted(
        entry
        for entry in names
        if f"journal/{entry}" in files or (ticket.dir / "journal" / entry).is_file()
    )


def merge_ticket(merge: Merge, ticket: TicketDirectory, files: dict[str, str]) -> None:
    """Merge a ticket this home has too; `files` maps each entry's path inside the ticket to its name."""
    is_local = not providers.load_manifest(ticket.source)["capabilities"]["fetch"]
    record = files.get(RECORD)
    theirs = layout.parse_json_object(record, merge.entries[record]) if record else {}
    mine = layout.read_json_object(ticket.dir / RECORD)
    raw = [name for within, name in files.items() if within.startswith("raw/")]
    mirror_taken = False
    if raw and not is_local:
        mirror_taken = merge_mirror(merge, ticket, raw, theirs=theirs, mine=mine)
    for within, name in files.items():
        if within == RECORD:
            merge_record(merge, ticket, files, mirror_taken=mirror_taken)
        elif is_local or name not in raw:
            merge_ticket_file(merge, ticket, within, name, is_local=is_local)


CONFIG_NAMES = (
    paths.ROOT_CONFIG_NAME,
    paths.NAMESPACE_CONFIG_NAME,
    paths.PRODUCT_CONFIG_NAME,
)


def is_config(name: str) -> bool:
    parts = name.split("/")
    return len(parts) <= len(CONFIG_NAMES) and parts[-1] == CONFIG_NAMES[len(parts) - 1]


def merge_value(
    mine: dict, key: str, value: object, *, path: str, kept: list[str]
) -> bool:
    """Merge one key of the archive's config into this home's; returns whether it changed."""
    if key not in mine:
        mine[key] = value
        return True
    current = mine[key]
    if current == value:
        return False
    if isinstance(current, dict) and isinstance(value, dict):
        changed = False
        for inner, inner_value in value.items():
            changed |= merge_value(
                current, inner, inner_value, path=f"{path}.{inner}", kept=kept
            )
        return changed
    if (
        key in config.LIST_KEYS
        and isinstance(current, list)
        and isinstance(value, list)
    ):
        mine[key] = current + [item for item in value if item not in current]
        return True
    kept.append(path)
    return False


def merge_config(merge: Merge, name: str) -> None:
    theirs = layout.parse_json_object(name, merge.entries[name])
    mine_bytes = merge.mine(name)
    if mine_bytes == merge.entries[name]:
        return
    mine = layout.parse_json_object(name, mine_bytes) if mine_bytes is not None else {}
    portable = {
        key: value for key, value in theirs.items() if key not in config.MACHINE_KEYS
    }
    if mine_bytes is None and len(portable) == len(theirs):
        merge.add(name)
    elif mine_bytes is None:
        merge.add(name, layout.json_bytes(portable))
    else:
        merged = copy.deepcopy(mine)
        kept: list[str] = []
        changed = sorted(
            key
            for key, value in portable.items()
            if merge_value(merged, key, value, path=key, kept=kept)
        )
        for path in kept:
            merge.keep_mine(name, f"keeps this home's {path}")
        if changed:
            merge.merge_keys(name, changed, layout.json_bytes(merged))
    dropped = [
        key
        for key in sorted(config.MACHINE_KEYS)
        if key in theirs and (key not in mine or theirs[key] != mine[key])
    ]
    if dropped:
        merge.leave_out(name, dropped)


WORKSPACE_PATH = re.compile(r"`((?:[A-Za-z]:[\\/]|/|~)[^`]*)`")


def workspace_section(plan: str) -> str:
    """The plan's `## Workspace` section, up to the next `## ` heading."""
    found = re.search(
        r"^## Workspace[ \t]*$(.*?)(?=^## |\Z)", plan, re.MULTILINE | re.DOTALL
    )
    return found.group(1) if found else ""


def missing_workspace_paths(plan: bytes) -> list[str]:
    text = plan.decode("utf-8", errors="replace").replace("\r\n", "\n")
    section = workspace_section(text)
    return [
        found
        for found in dict.fromkeys(WORKSPACE_PATH.findall(section))
        if not Path(found).expanduser().exists()
    ]


def build(manifest: Manifest, entries: dict[str, bytes]) -> Merge:
    merge = Merge(paths.sdlc_home(), entries, manifest["created_at"])
    tickets: dict[TicketDirectory, dict[str, str]] = {}
    for name in sorted(entries):
        located = locate(name)
        if located:
            ticket, within = located
            tickets.setdefault(ticket, {})[within] = name
        elif is_config(name):
            merge_config(merge, name)
        else:
            merge_file(merge, name)
    in_order = sorted(tickets.items(), key=lambda item: item[0].qualified)
    for ticket, files in in_order:
        if ticket.dir.is_dir():
            merge_ticket(merge, ticket, files)
        else:
            merge.add_ticket(ticket, list(files.values()))
    for ticket, files in in_order:
        plan = files.get(ASKED_FILES[0])
        missing = missing_workspace_paths(entries[plan]) if plan else []
        if missing:
            merge.report_missing_paths(ticket, missing)
    return merge


def report(archive_text: str, cwd: Path) -> ImportReport:
    manifest, entries = load(archive_text, cwd)
    merge = build(manifest, entries)
    return {**merge.summary(), "digest": merge.digest()}


def write(path: Path, content: bytes, *, is_new: bool) -> None:
    if not is_new:
        layout.replace_file(path, content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive: a file that appeared since the digest was checked is never overwritten.
    with path.open("xb") as created:
        created.write(content)


def check_choices(
    merge: Merge, *, take_theirs: list[str], keep_mine: list[str]
) -> None:
    both = sorted(set(take_theirs) & set(keep_mine))
    unasked = sorted(set(take_theirs + keep_mine) - set(merge.conflicts))
    unchosen = sorted(set(merge.conflicts) - set(take_theirs + keep_mine))
    problems = [
        *(f"{ref} is given both --take-theirs and --keep-mine" for ref in both),
        *(f"{ref} has no conflict to choose for" for ref in unasked),
        *(f"{ref} has a conflict and no choice" for ref in unchosen),
    ]
    if problems:
        raise SdlcError(
            "; ".join(problems),
            hint="Nothing was written. Pass --take-theirs or --keep-mine "
            "once for each ticket the report lists under conflicts.",
        )


def apply(
    archive_text: str,
    *,
    digest: str,
    take_theirs: list[str],
    keep_mine: list[str],
    cwd: Path,
) -> ApplyReport:
    manifest, entries = load(archive_text, cwd)
    merge = build(manifest, entries)
    if merge.digest() != digest:
        raise SdlcError(
            "the SDLC home or the archive changed since the report",
            hint="Nothing was written. Run `archive import` without --apply "
            "again and review the new report.",
        )
    check_choices(merge, take_theirs=take_theirs, keep_mine=keep_mine)
    writes = merge.writes + [
        planned for ref in take_theirs for planned in merge.theirs_writes[ref]
    ]
    clashes = [w.path for w in writes if w.is_new and (merge.home / w.path).exists()]
    if clashes:
        raise SdlcError(
            "files appeared since the report: " + ", ".join(clashes),
            hint="Nothing was written. Run `archive import` without --apply again.",
        )
    for planned in writes:
        write(merge.home / planned.path, planned.content, is_new=planned.is_new)
    return {**merge.summary(), "digest": digest, "applied": True}
