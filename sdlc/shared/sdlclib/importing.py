"""
`archive import`: merge an archive that `archive export` wrote into the SDLC home.

Without `apply` it only reports what the merge would do. The merge rules are in
`shared/archive.md`.
"""

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path, PurePosixPath

from . import layout, paths, providers
from .archive import FORMAT_NAME, FORMAT_VERSION, MANIFEST_NAME
from .errors import SdlcError


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


def check_manifest(path: Path, entries: dict[str, bytes]) -> dict:
    if MANIFEST_NAME not in entries:
        raise SdlcError(f"{path} has no {MANIFEST_NAME}, so it is not an sdlc archive")
    try:
        manifest = json.loads(entries.pop(MANIFEST_NAME))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SdlcError(
            f"{path}: {MANIFEST_NAME} is not valid JSON ({error})"
        ) from error
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT_NAME:
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
    return manifest


def in_layout(name: str) -> bool:
    """Whether an entry names a file inside a home; anything else could land outside it."""
    if "\\" in name or ":" in name or name.startswith("/"):
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if len(parts) == 1:
        return name == "sdlc.json"
    if not all(layout.is_name(part) for part in parts[:-1][:2]):
        return False
    if len(parts) >= 5 and parts[2] in providers.list_sources():
        return layout.is_name(parts[3])
    return True


def load(archive_text: str, cwd: Path) -> tuple[dict, dict[str, bytes]]:
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


def ticket_ref(relative: str) -> str | None:
    parts = relative.split("/")
    if len(parts) < 5 or parts[2] not in providers.list_sources():
        return None
    return f"{parts[0]}/{parts[1]}/{parts[2]}:{parts[3]}"


@dataclass
class Write:
    path: str
    content: bytes
    new: bool


@dataclass
class Merge:
    """What importing the archive would do to the home, and the writes that do it."""

    home: Path
    entries: dict[str, bytes]
    created_at: str
    adds: list[str] = field(default_factory=list)
    new_tickets: list[str] = field(default_factory=list)
    kept_mine: list[dict] = field(default_factory=list)
    kept_both: list[dict] = field(default_factory=list)
    mirrors: list[dict] = field(default_factory=list)
    merges: list[dict] = field(default_factory=list)
    not_imported: list[dict] = field(default_factory=list)
    missing_workspace_paths: list[dict] = field(default_factory=list)
    conflicts: dict[str, list[str]] = field(default_factory=dict)
    writes: list[Write] = field(default_factory=list)
    theirs_writes: dict[str, list[Write]] = field(default_factory=dict)

    def mine(self, name: str) -> bytes | None:
        path = self.home / name
        return path.read_bytes() if path.is_file() else None

    def add(self, name: str) -> None:
        self.adds.append(name)
        self.writes.append(Write(name, self.entries[name], True))

    def replace(self, name: str, content: bytes) -> None:
        self.writes.append(Write(name, content, False))

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
        self.writes.append(Write(beside, content, True))

    def conflict(self, ref: str, file: str, theirs: Write) -> None:
        """Ask keep-mine or take-theirs for the ticket; `theirs` is written only on take-theirs."""
        self.conflicts.setdefault(ref, []).append(file)
        self.theirs_writes.setdefault(ref, []).append(theirs)

    def summary(self) -> dict:
        return {
            "adds": self.adds,
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


def within_ticket(name: str) -> str:
    return "/".join(name.split("/")[4:])


def merge_file(merge: Merge, name: str, ref: str | None, local: bool) -> None:
    mine = merge.mine(name)
    within = within_ticket(name) if ref else ""
    if mine is None:
        merge.add(name)
    elif mine == merge.entries[name]:
        return
    elif ref and within.startswith("journal/"):
        merge.keep_mine(name, "a journal entry of the same name is already here")
    elif ref and (within in ASKED_FILES or (local and within.startswith("raw/"))):
        merge.conflict(ref, within, Write(name, merge.entries[name], False))
    else:
        merge.keep_both(name)


def parse_record(name: str, content: bytes | None) -> dict:
    if content is None:
        return {}
    try:
        record = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SdlcError(f"{name} is not a valid ticket record ({error})") from error
    if not isinstance(record, dict):
        raise SdlcError(f"{name} must hold a JSON object")
    return record


def is_newer(theirs: dict, mine: dict) -> bool:
    """Whether the archive's mirror is of a later revision than this home's."""
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
    merge: Merge, ref: str, raw: list[str], theirs: dict, mine: dict
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
    merge.mirrors.append(
        {
            "ticket": ref,
            "mine": mine.get("fingerprint"),
            "theirs": theirs.get("fingerprint"),
            "taken": taken,
        }
    )
    for name in differing if taken else []:
        if merge.mine(name) is None:
            merge.add(name)
        else:
            merge.replace(name, merge.entries[name])
    return taken


def merge_record(merge: Merge, ref: str, name: str, mirror_taken: bool) -> None:
    mine_bytes = merge.mine(name)
    if mine_bytes is None:
        merge.add(name)
        return
    if mine_bytes == merge.entries[name]:
        return
    mine = parse_record(name, mine_bytes)
    theirs = parse_record(name, merge.entries[name])
    merged = dict(mine)
    if mirror_taken:
        merged.update({key: theirs[key] for key in MIRROR_KEYS if key in theirs})
    unposted = unposted_union(merge, name, mine, theirs)
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
        merge.merges.append({"path": name, "keys": changed})
        merge.replace(name, record_bytes(merged))
    if asked:
        taken = {**merged, **{key: theirs[key] for key in asked}}
        merge.conflict(ref, RECORD, Write(name, record_bytes(taken), False))


def unposted_union(merge: Merge, name: str, mine: dict, theirs: dict) -> list[str]:
    """Entries either home has not posted yet still wait; checkpoint skips one already posted."""
    journal = name.rsplit("/", 1)[0] + "/journal/"
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
        if journal + entry in merge.entries or merge.mine(journal + entry) is not None
    )


def record_bytes(record: dict) -> bytes:
    return (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode()


def merge_ticket(merge: Merge, ref: str, names: list[str]) -> None:
    prefix = "/".join(names[0].split("/")[:4])
    local = not providers.load_manifest(names[0].split("/")[2])["capabilities"]["fetch"]
    record_name = f"{prefix}/{RECORD}"
    theirs = parse_record(record_name, merge.entries.get(record_name))
    mine = parse_record(record_name, merge.mine(record_name))
    raw = [name for name in names if within_ticket(name).startswith("raw/")]
    mirror_taken = False
    if raw and not local:
        mirror_taken = merge_mirror(merge, ref, raw, theirs, mine)
    for name in names:
        if name == record_name:
            merge_record(merge, ref, name, mirror_taken)
        elif local or name not in raw:
            merge_file(merge, name, ref, local)


CONFIG_NAMES = ("sdlc.json", "namespace.json", "product.json")
# Directories on the machine an archive came from, which mean nothing on this one.
MACHINE_KEYS = ("scan_roots", "worktree_root")
LIST_KEYS = ("protected_branches", "sensitive")


def is_config(name: str) -> bool:
    parts = name.split("/")
    return len(parts) <= 3 and parts[-1] == CONFIG_NAMES[len(parts) - 1]


def parse_config(name: str, content: bytes) -> dict:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SdlcError(f"{name} is not valid JSON ({error})") from error
    if not isinstance(data, dict):
        raise SdlcError(f"{name} must hold a JSON object")
    return data


def merge_value(
    mine: dict, key: str, value: object, path: str, kept: list[str]
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
            changed |= merge_value(current, inner, inner_value, f"{path}.{inner}", kept)
        return changed
    if key in LIST_KEYS and isinstance(current, list) and isinstance(value, list):
        mine[key] = current + [item for item in value if item not in current]
        return True
    kept.append(path)
    return False


def merge_config(merge: Merge, name: str) -> None:
    theirs = parse_config(name, merge.entries[name])
    dropped = [key for key in MACHINE_KEYS if key in theirs]
    mine_bytes = merge.mine(name)
    if mine_bytes is None:
        merge.adds.append(name)
        content = merge.entries[name]
        if dropped:
            portable = {k: v for k, v in theirs.items() if k not in MACHINE_KEYS}
            content = record_bytes(portable)
        merge.writes.append(Write(name, content, True))
    elif mine_bytes != merge.entries[name]:
        mine = parse_config(name, mine_bytes)
        merged = json.loads(json.dumps(mine))
        dropped = [key for key in dropped if theirs[key] != mine.get(key)]
        kept: list[str] = []
        changed = [
            key
            for key, value in theirs.items()
            if key not in MACHINE_KEYS and merge_value(merged, key, value, key, kept)
        ]
        merge.kept_mine.extend(
            {"path": name, "reason": f"keeps this home's {path}"} for path in kept
        )
        if changed:
            merge.merges.append({"path": name, "keys": sorted(changed)})
            merge.replace(name, record_bytes(merged))
    else:
        dropped = []
    if dropped:
        merge.not_imported.append({"path": name, "keys": dropped})


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


def build(manifest: dict, entries: dict[str, bytes]) -> Merge:
    merge = Merge(paths.sdlc_home(), entries, manifest["created_at"])
    tickets: dict[str, list[str]] = {}
    for name in sorted(entries):
        ref = ticket_ref(name)
        if ref:
            tickets.setdefault(ref, []).append(name)
        elif is_config(name):
            merge_config(merge, name)
        else:
            merge_file(merge, name, None, False)
    for ref, names in sorted(tickets.items()):
        if not (merge.home / "/".join(names[0].split("/")[:4])).is_dir():
            merge.new_tickets.append(ref)
            for name in names:
                merge.add(name)
        else:
            merge_ticket(merge, ref, names)
    for ref, names in sorted(tickets.items()):
        plan = next((n for n in names if within_ticket(n) == ASKED_FILES[0]), None)
        missing = missing_workspace_paths(entries[plan]) if plan else []
        if missing:
            merge.missing_workspace_paths.append({"ticket": ref, "paths": missing})
    merge.adds.sort()
    return merge


def report(archive_text: str, cwd: Path) -> dict:
    manifest, entries = load(archive_text, cwd)
    merge = build(manifest, entries)
    return {**merge.summary(), "digest": merge.digest()}


def write(path: Path, content: bytes, new: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if new:
        # Exclusive: a file that appeared since the digest was checked is never overwritten.
        with path.open("xb") as created:
            created.write(content)
        return
    scratch = path.with_name(path.name + ".import.tmp")
    scratch.write_bytes(content)
    os.replace(scratch, path)


def check_choices(merge: Merge, take_theirs: list[str], keep_mine: list[str]) -> None:
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
    digest: str,
    take_theirs: list[str],
    keep_mine: list[str],
    cwd: Path,
) -> dict:
    manifest, entries = load(archive_text, cwd)
    merge = build(manifest, entries)
    if merge.digest() != digest:
        raise SdlcError(
            "the SDLC home or the archive changed since the report",
            hint="Nothing was written. Run `archive import` without --apply "
            "again and review the new report.",
        )
    check_choices(merge, take_theirs, keep_mine)
    writes = merge.writes + [
        planned for ref in take_theirs for planned in merge.theirs_writes[ref]
    ]
    clashes = [w.path for w in writes if w.new and (merge.home / w.path).exists()]
    if clashes:
        raise SdlcError(
            "files appeared since the report: " + ", ".join(clashes),
            hint="Nothing was written. Run `archive import` without --apply again.",
        )
    for planned in writes:
        write(merge.home / planned.path, planned.content, planned.new)
    return {**merge.summary(), "digest": digest, "applied": True}
