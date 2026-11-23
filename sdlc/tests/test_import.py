import json
import shutil
import zipfile
from pathlib import Path

import pytest

TICKET = "acme/billing-app/github/1234"
REF = "acme/billing-app/github:1234"


def put(home: Path, relative: str, content: str | dict) -> Path:
    path = home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if isinstance(content, str) else json.dumps(content)
    path.write_text(text, encoding="utf-8")
    return path


def read(home: Path, relative: str) -> str:
    return (home / relative).read_text(encoding="utf-8")


def files_of(home: Path) -> dict[str, str]:
    return {
        path.relative_to(home).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(home.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def source_home(tmp_path: Path) -> Path:
    """The other machine's SDLC home, where the archive is exported from."""
    home = tmp_path / "source-home"
    put(home, "sdlc.json", {"default_namespace": "acme"})
    put(home, "acme/namespace.json", {"sources": {"github": {"owner": "acme"}}})
    put(
        home,
        "acme/billing-app/product.json",
        {"sources": {"github": {"repository": "billing-app"}}},
    )
    put(
        home,
        f"{TICKET}/ticket.json",
        {
            "source": "github",
            "id": "1234",
            "title": "Retry exports",
            "type": "task",
            "fingerprint": {"sha256": "aaa"},
            "last_fetched_at": "2026-11-20T10:00:00Z",
        },
    )
    put(home, f"{TICKET}/raw/raw.json", '{"title": "Retry exports"}')
    put(home, f"{TICKET}/journal/2026-11-20T10-00-00Z.md", "# entry one")
    put(home, f"{TICKET}/plan.md", "# plan")
    put(home, f"{TICKET}/artifacts/probe.py", "print(1)")
    return home


@pytest.fixture
def same_home(source_home: Path, sdlc_home: Path) -> Path:
    """This machine's home, starting as a copy of the other machine's."""
    shutil.copytree(source_home, sdlc_home)
    return sdlc_home


@pytest.fixture
def export(run_cli, source_home: Path, tmp_path: Path):
    def run(scope: str | None = None) -> Path:
        result = run_cli(
            "archive",
            "export",
            *([scope] if scope else []),
            "--out",
            str(tmp_path),
            home=source_home,
            cwd=tmp_path,
        )
        assert result.code == 0, result.err
        return Path(result.json["archive"])

    return run


@pytest.fixture
def import_archive(run_cli, tmp_path: Path):
    def run(archive: Path, *flags: str):
        return run_cli("archive", "import", str(archive), *flags, cwd=tmp_path)

    return run


@pytest.fixture
def apply(import_archive):
    """Report, then apply with the report's digest and the choices given."""

    def run(archive: Path, *choices: str):
        report = import_archive(archive)
        assert report.code == 0, report.err
        result = import_archive(
            archive, "--apply", "--digest", report.json["digest"], *choices
        )
        assert result.code == 0, result.err
        return result.json

    return run


def test_the_report_into_an_empty_home_lists_every_file_as_an_add_and_writes_nothing(
    import_archive, export, sdlc_home: Path
):
    archive = export()

    result = import_archive(archive)

    assert result.code == 0, result.err
    report = result.json
    assert report["adds"] == [
        "acme/billing-app/github/1234/artifacts/probe.py",
        "acme/billing-app/github/1234/journal/2026-11-20T10-00-00Z.md",
        "acme/billing-app/github/1234/plan.md",
        "acme/billing-app/github/1234/raw/raw.json",
        "acme/billing-app/github/1234/ticket.json",
        "acme/billing-app/product.json",
        "acme/namespace.json",
        "sdlc.json",
    ]
    assert report["new_tickets"] == [REF]
    assert report["conflicts"] == []
    assert not sdlc_home.exists()


def test_applying_into_an_empty_home_writes_the_archive_as_it_was_exported(
    apply, export, source_home: Path, sdlc_home: Path
):
    archive = export()

    applied = apply(archive)

    assert applied["applied"] is True
    assert files_of(sdlc_home) == files_of(source_home)


def make_zip(path: Path, entries: dict[str, str | dict]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            text = content if isinstance(content, str) else json.dumps(content)
            archive.writestr(name, text)
    return path


MANIFEST = {
    "format": "sdlc-archive",
    "version": 1,
    "scope": {"kind": "home", "ref": None},
    "created_at": "2026-11-23T14:05:09Z",
    "source_home": "/home/dev/.sdlc",
    "tickets": [],
}


@pytest.mark.parametrize(
    ("manifest", "named"),
    [
        (None, "manifest.json"),
        ({**MANIFEST, "version": 2}, "version 2"),
        ({**MANIFEST, "format": "something-else"}, "sdlc archive"),
        ({**MANIFEST, "created_at": "../../x"}, "created_at"),
    ],
)
def test_an_archive_without_a_manifest_of_a_known_version_is_refused(
    import_archive, tmp_path: Path, sdlc_home: Path, manifest: dict | None, named: str
):
    entries = {"sdlc.json": {}} | ({"manifest.json": manifest} if manifest else {})
    archive = make_zip(tmp_path / "odd.zip", entries)

    result = import_archive(archive)

    assert result.code == 1
    assert named in result.err
    assert not sdlc_home.exists()


@pytest.mark.parametrize(
    "entry",
    [
        "../escaped.md",
        "acme/../../escaped.md",
        "/etc/escaped.md",
        "C:/escaped.md",
        r"acme\..\..\escaped.md",
        "Acme/namespace.json",
    ],
)
def test_an_entry_outside_the_layout_of_a_home_is_refused_before_anything_is_written(
    import_archive, tmp_path: Path, sdlc_home: Path, entry: str
):
    archive = make_zip(
        tmp_path / "evil.zip",
        {"manifest.json": MANIFEST, "sdlc.json": {}, entry: "x"},
    )

    report = import_archive(archive)
    applied = import_archive(archive, "--apply", "--digest", "0" * 64)

    assert report.code == 1
    assert "not a path in an SDLC home" in report.err
    assert applied.code == 1
    assert not sdlc_home.exists()
    assert not (tmp_path / "escaped.md").exists()


def test_journal_entries_from_both_homes_are_kept(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    put(source_home, f"{TICKET}/journal/2026-11-21T09-00-00Z.md", "# theirs")
    put(same_home, f"{TICKET}/journal/2026-11-22T09-00-00Z.md", "# mine")
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["adds"] == [f"{TICKET}/journal/2026-11-21T09-00-00Z.md"]
    assert report["new_tickets"] == []
    assert report["conflicts"] == []
    assert sorted(p.name for p in (same_home / TICKET / "journal").iterdir()) == [
        "2026-11-20T10-00-00Z.md",
        "2026-11-21T09-00-00Z.md",
        "2026-11-22T09-00-00Z.md",
    ]
    assert read(same_home, f"{TICKET}/journal/2026-11-22T09-00-00Z.md") == "# mine"


def test_a_journal_entry_of_the_same_name_keeps_this_homes_copy(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    put(same_home, f"{TICKET}/journal/2026-11-20T10-00-00Z.md", "# mine")
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["kept_mine"] == [
        {
            "path": f"{TICKET}/journal/2026-11-20T10-00-00Z.md",
            "reason": "a journal entry of the same name is already here",
        }
    ]
    assert report["conflicts"] == []
    assert read(same_home, f"{TICKET}/journal/2026-11-20T10-00-00Z.md") == "# mine"


def test_applying_after_the_home_changed_since_the_report_is_refused_and_writes_nothing(
    import_archive, export, source_home: Path, same_home: Path
):
    put(source_home, f"{TICKET}/journal/2026-11-21T09-00-00Z.md", "# theirs")
    archive = export()
    digest = import_archive(archive).json["digest"]
    put(same_home, f"{TICKET}/plan.md", "# edited after the report")

    result = import_archive(archive, "--apply", "--digest", digest)

    assert result.code == 1
    assert "changed since the report" in result.err
    assert not (same_home / TICKET / "journal" / "2026-11-21T09-00-00Z.md").exists()


@pytest.mark.parametrize("name", ["plan.md", "pulls.md"])
def test_a_differing_plan_or_pull_request_record_is_a_conflict_of_its_ticket(
    import_archive, export, source_home: Path, same_home: Path, name: str
):
    put(source_home, f"{TICKET}/{name}", "# theirs")
    put(same_home, f"{TICKET}/{name}", "# mine")

    report = import_archive(export()).json

    assert report["conflicts"] == [{"ticket": REF, "files": [name]}]


@pytest.mark.parametrize(
    ("choice", "kept"), [("--take-theirs", "# theirs"), ("--keep-mine", "# mine")]
)
def test_a_conflict_is_resolved_by_the_choice_made_for_its_ticket(
    apply, export, source_home: Path, same_home: Path, choice: str, kept: str
):
    put(source_home, f"{TICKET}/plan.md", "# theirs")
    put(same_home, f"{TICKET}/plan.md", "# mine")

    apply(export(), choice, REF)

    assert read(same_home, f"{TICKET}/plan.md") == kept


@pytest.mark.parametrize(
    ("choices", "named"),
    [
        ([], REF),
        (["--take-theirs", "acme/billing-app/github:99"], "acme/billing-app/github:99"),
        (["--take-theirs", REF, "--keep-mine", REF], REF),
    ],
)
def test_applying_refuses_a_conflict_without_exactly_one_choice(
    import_archive, export, source_home: Path, same_home: Path, choices, named
):
    put(source_home, f"{TICKET}/plan.md", "# theirs")
    put(source_home, f"{TICKET}/journal/2026-11-21T09-00-00Z.md", "# theirs")
    put(same_home, f"{TICKET}/plan.md", "# mine")
    archive = export()
    digest = import_archive(archive).json["digest"]

    result = import_archive(archive, "--apply", "--digest", digest, *choices)

    assert result.code == 1
    assert named in result.err
    assert read(same_home, f"{TICKET}/plan.md") == "# mine"
    assert not (same_home / TICKET / "journal" / "2026-11-21T09-00-00Z.md").exists()


def test_a_differing_artifact_is_kept_beside_this_homes_copy_under_a_suffixed_name(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    put(same_home, f"{TICKET}/artifacts/probe.py", "print('mine')")
    archive = export()
    created = json.loads(zipfile.ZipFile(archive).read("manifest.json"))[
        "created_at"
    ].replace(":", "-")
    suffixed = f"{TICKET}/artifacts/probe.imported-{created}.py"

    report = import_archive(archive).json
    apply(archive)

    assert report["kept_both"] == [
        {"path": f"{TICKET}/artifacts/probe.py", "as": suffixed}
    ]
    assert report["conflicts"] == []
    assert read(same_home, f"{TICKET}/artifacts/probe.py") == "print('mine')"
    assert read(same_home, suffixed) == "print(1)"


def test_importing_the_same_archive_twice_changes_nothing_the_second_time(
    apply, import_archive, export, same_home: Path
):
    put(same_home, f"{TICKET}/artifacts/probe.py", "print('mine')")
    archive = export()
    apply(archive)
    before = files_of(same_home)

    report = import_archive(archive).json
    apply(archive)

    assert report["adds"] == []
    assert report["kept_both"] == []
    assert files_of(same_home) == before


ADO = "acme/billing-app/ado/77"
ADO_REF = "acme/billing-app/ado:77"


def ado_ticket(home: Path, rev: int, title: str) -> None:
    put(
        home,
        f"{ADO}/ticket.json",
        {
            "source": "ado",
            "id": "77",
            "title": title,
            "type": "bug",
            "fingerprint": {"rev": rev},
            "last_fetched_at": f"2026-11-{10 + rev:02d}T00:00:00Z",
        },
    )
    put(home, f"{ADO}/raw/raw.json", json.dumps({"rev": rev, "title": title}))


def test_a_mirror_with_a_newer_revision_replaces_this_homes_and_its_record_follows(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    ado_ticket(source_home, 5, "Fix export")
    put(source_home, f"{ADO}/raw/screenshot.png", "png")
    ado_ticket(same_home, 3, "Fix exports")
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["mirrors"] == [
        {"ticket": ADO_REF, "mine": {"rev": 3}, "theirs": {"rev": 5}, "taken": True}
    ]
    assert report["conflicts"] == []
    assert json.loads(read(same_home, f"{ADO}/raw/raw.json"))["rev"] == 5
    assert read(same_home, f"{ADO}/raw/screenshot.png") == "png"
    record = json.loads(read(same_home, f"{ADO}/ticket.json"))
    assert record["fingerprint"] == {"rev": 5}
    assert record["title"] == "Fix export"
    assert record["last_fetched_at"] == "2026-11-15T00:00:00Z"


def test_a_mirror_with_an_older_revision_leaves_this_homes_untouched(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    ado_ticket(source_home, 2, "Fix export")
    put(source_home, f"{ADO}/raw/screenshot.png", "png")
    ado_ticket(same_home, 3, "Fix exports")
    before = files_of(same_home)
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["mirrors"] == [
        {"ticket": ADO_REF, "mine": {"rev": 3}, "theirs": {"rev": 2}, "taken": False}
    ]
    assert report["conflicts"] == []
    assert files_of(same_home) == before


def test_a_mirror_without_a_revision_number_is_newer_when_it_was_fetched_later(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    record = json.loads(read(source_home, f"{TICKET}/ticket.json"))
    put(
        source_home,
        f"{TICKET}/ticket.json",
        {
            **record,
            "fingerprint": {"sha256": "bbb"},
            "last_fetched_at": "2026-11-22T00:00:00Z",
        },
    )
    put(source_home, f"{TICKET}/raw/raw.json", '{"title": "newer"}')
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["mirrors"] == [
        {
            "ticket": REF,
            "mine": {"sha256": "aaa"},
            "theirs": {"sha256": "bbb"},
            "taken": True,
        }
    ]
    assert read(same_home, f"{TICKET}/raw/raw.json") == '{"title": "newer"}'
    assert json.loads(read(same_home, f"{TICKET}/ticket.json"))["fingerprint"] == {
        "sha256": "bbb"
    }


def record_of(home: Path, ticket: str = TICKET) -> dict:
    return json.loads(read(home, f"{ticket}/ticket.json"))


def change_record(home: Path, **changes) -> None:
    record = {**record_of(home), **changes}
    put(
        home,
        f"{TICKET}/ticket.json",
        {k: v for k, v in record.items() if v is not None},
    )


def test_a_record_key_only_the_archive_has_is_added_without_asking(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    change_record(same_home, type=None)
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["conflicts"] == []
    assert report["merges"] == [{"path": f"{TICKET}/ticket.json", "keys": ["type"]}]
    assert record_of(same_home)["type"] == "task"


@pytest.mark.parametrize(
    ("choice", "kept"), [("--take-theirs", "task"), ("--keep-mine", "bug")]
)
def test_a_record_key_both_homes_set_differently_is_a_conflict_of_its_ticket(
    apply, import_archive, export, same_home: Path, choice: str, kept: str
):
    change_record(same_home, type="bug")
    archive = export()

    report = import_archive(archive).json
    apply(archive, choice, REF)

    assert report["conflicts"] == [{"ticket": REF, "files": ["ticket.json"]}]
    assert record_of(same_home)["type"] == kept


def test_unposted_journal_entries_of_both_homes_still_wait_to_be_posted(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    change_record(source_home, unposted_journal=["2026-11-20T10-00-00Z.md"])
    put(same_home, f"{TICKET}/journal/2026-11-22T09-00-00Z.md", "# mine")
    change_record(same_home, unposted_journal=["2026-11-22T09-00-00Z.md"])
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert report["conflicts"] == []
    assert record_of(same_home)["unposted_journal"] == [
        "2026-11-20T10-00-00Z.md",
        "2026-11-22T09-00-00Z.md",
    ]


def test_a_differing_ticket_file_of_a_local_ticket_is_a_conflict_of_its_ticket(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    local = "acme/billing-app/local/retry-exports"
    put(source_home, f"{local}/ticket.json", {"source": "local", "id": "retry-exports"})
    put(source_home, f"{local}/raw/ticket.md", "# theirs")
    put(same_home, f"{local}/ticket.json", {"source": "local", "id": "retry-exports"})
    put(same_home, f"{local}/raw/ticket.md", "# mine")
    archive = export()

    report = import_archive(archive).json
    apply(archive, "--take-theirs", "acme/billing-app/local:retry-exports")

    assert report["conflicts"] == [
        {"ticket": "acme/billing-app/local:retry-exports", "files": ["raw/ticket.md"]}
    ]
    assert report["mirrors"] == []
    assert read(same_home, f"{local}/raw/ticket.md") == "# theirs"


def config_of(home: Path, relative: str) -> dict:
    return json.loads(read(home, relative))


def test_this_homes_scan_roots_and_worktree_root_are_never_replaced(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    put(
        source_home,
        "sdlc.json",
        {
            "default_namespace": "acme",
            "scan_roots": ["C:/theirs"],
            "worktree_root": "C:/wt",
        },
    )
    put(same_home, "sdlc.json", {"scan_roots": ["D:/mine"], "worktree_root": "D:/wt"})
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert config_of(same_home, "sdlc.json") == {
        "scan_roots": ["D:/mine"],
        "worktree_root": "D:/wt",
        "default_namespace": "acme",
    }
    assert report["merges"] == [{"path": "sdlc.json", "keys": ["default_namespace"]}]
    assert report["not_imported"] == [
        {"path": "sdlc.json", "keys": ["scan_roots", "worktree_root"]}
    ]
    assert report["conflicts"] == []


def test_a_config_file_new_to_this_home_arrives_without_the_other_machines_paths(
    apply, import_archive, export, source_home: Path, sdlc_home: Path
):
    put(
        source_home,
        "acme/billing-app/product.json",
        {
            "sources": {"github": {"repository": "billing-app"}},
            "scan_roots": ["C:/code"],
        },
    )
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert "acme/billing-app/product.json" in report["adds"]
    assert report["not_imported"] == [
        {"path": "acme/billing-app/product.json", "keys": ["scan_roots"]}
    ]
    assert config_of(sdlc_home, "acme/billing-app/product.json") == {
        "sources": {"github": {"repository": "billing-app"}}
    }


def test_bindings_and_defaults_merge_and_this_homes_values_win_where_both_set_one(
    apply, import_archive, export, source_home: Path, same_home: Path
):
    put(
        source_home,
        "acme/namespace.json",
        {
            "sources": {
                "github": {"owner": "acme-old"},
                "ado": {"organization": "contoso"},
            },
            "default_product": "billing-app",
            "default_source": "ado",
            "protected_branches": ["release/*"],
        },
    )
    put(
        same_home,
        "acme/namespace.json",
        {
            "sources": {"github": {"owner": "acme"}},
            "default_source": "github",
            "protected_branches": ["main"],
        },
    )
    archive = export()

    report = import_archive(archive).json
    apply(archive)

    assert config_of(same_home, "acme/namespace.json") == {
        "sources": {"github": {"owner": "acme"}, "ado": {"organization": "contoso"}},
        "default_source": "github",
        "protected_branches": ["main", "release/*"],
        "default_product": "billing-app",
    }
    assert report["kept_mine"] == [
        {"path": "acme/namespace.json", "reason": "keeps this home's default_source"},
        {
            "path": "acme/namespace.json",
            "reason": "keeps this home's sources.github.owner",
        },
    ]
    assert report["conflicts"] == []


def test_the_report_lists_the_workspace_paths_of_a_plan_missing_on_this_machine(
    import_archive, export, source_home: Path, tmp_path: Path
):
    here, gone = tmp_path, tmp_path / "gone" / "billing-app"
    put(
        source_home,
        f"{TICKET}/plan.md",
        f"""# Implementation Plan

## Workspace

### Scan roots

- `{here}` - default scan root

### Worktrees

| Repository  | Branch | Kind | Path      |
| ----------- | ------ | ---- | --------- |
| billing-app | main   | main | `{gone}` |

### Projects

| Project | Lives in    | Path       | Technology |
| ------- | ----------- | ---------- | ---------- |
| api     | billing-app | `src/api`  | .NET       |

## Phase 1: Build

**Target:** `{tmp_path / "elsewhere" / "file.cs"}`
""",
    )

    report = import_archive(export()).json

    assert report["missing_workspace_paths"] == [{"ticket": REF, "paths": [str(gone)]}]


def test_nothing_in_this_home_is_deleted(
    apply, export, source_home: Path, same_home: Path
):
    ado_ticket(source_home, 5, "Fix export")
    ado_ticket(same_home, 3, "Fix export")
    put(same_home, f"{ADO}/raw/old-attachment.png", "old")
    put(same_home, "personal/default/local/learn-rust/ticket.json", "{}")
    put(same_home, f"{TICKET}/artifacts/mine-only.md", "mine")
    before = set(files_of(same_home))

    apply(export())

    assert before <= set(files_of(same_home))
    assert json.loads(read(same_home, f"{ADO}/raw/raw.json"))["rev"] == 5


@pytest.mark.parametrize(
    ("scope", "prefixes"),
    [
        (None, ("",)),
        ("acme", ("sdlc.json", "acme/")),
        ("acme/notes-app", ("sdlc.json", "acme/namespace.json", "acme/notes-app/")),
        (
            "personal/default/local:learn-rust",
            (
                "sdlc.json",
                "personal/namespace.json",
                "personal/default/local/learn-rust/",
            ),
        ),
    ],
)
def test_a_scope_exported_on_one_machine_arrives_whole_on_another(
    apply, export, source_home: Path, sdlc_home: Path, scope, prefixes
):
    put(source_home, "acme/notes-app/product.json", {})
    put(source_home, "acme/notes-app/github/7/ticket.json", {"source": "github"})
    put(source_home, "personal/namespace.json", {"default_source": "local"})
    put(source_home, "personal/default/local/learn-rust/raw/ticket.md", "# rust")

    apply(export(scope))

    expected = {
        name: text
        for name, text in files_of(source_home).items()
        if name.startswith(prefixes)
    }
    assert files_of(sdlc_home) == expected
