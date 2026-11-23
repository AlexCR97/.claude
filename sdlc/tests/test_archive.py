import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.fixture
def home(sdlc_home: Path, write_config, make_ticket) -> Path:
    """Two namespaces, three products, four tickets, and a config file at every level."""
    write_config("sdlc.json", {"default_namespace": "acme"})
    write_config("acme/namespace.json", {"sources": {"github": {"owner": "acme"}}})
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"github": {"repository": "billing-app"}}},
    )
    write_config("acme/notes-app/product.json", {"scan_roots": ["C:/code"]})
    write_config("personal/namespace.json", {"default_source": "local"})

    billing = make_ticket("acme", "billing-app", "github", "1234")
    (billing / "ticket.json").write_text('{"source": "github"}', encoding="utf-8")
    (billing / "raw").mkdir()
    (billing / "raw" / "raw.json").write_text("{}", encoding="utf-8")
    (billing / "journal").mkdir()
    (billing / "journal" / "2026-11-20T10-00-00Z.md").write_text(
        "# entry", encoding="utf-8"
    )
    (billing / "plan.md").write_text("# plan", encoding="utf-8")

    other = make_ticket("acme", "billing-app", "local", "retry-exports")
    (other / "ticket.json").write_text('{"source": "local"}', encoding="utf-8")

    notes = make_ticket("acme", "notes-app", "github", "7")
    (notes / "ticket.json").write_text("{}", encoding="utf-8")

    idea = make_ticket("personal", "default", "local", "learn-rust")
    (idea / "ticket.json").write_text("{}", encoding="utf-8")
    return sdlc_home


def entries(archive: Path) -> set[str]:
    with zipfile.ZipFile(archive) as opened:
        return set(opened.namelist())


def manifest(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as opened:
        return json.loads(opened.read("manifest.json"))


def test_with_no_scope_the_whole_home_is_archived(run_cli, home: Path, tmp_path: Path):
    result = run_cli("archive", "export", cwd=tmp_path)

    assert result.code == 0, result.err
    archive = Path(result.json["archive"])
    assert archive.parent == tmp_path
    assert entries(archive) == {
        "manifest.json",
        "sdlc.json",
        "acme/namespace.json",
        "acme/billing-app/product.json",
        "acme/billing-app/github/1234/ticket.json",
        "acme/billing-app/github/1234/raw/raw.json",
        "acme/billing-app/github/1234/journal/2026-11-20T10-00-00Z.md",
        "acme/billing-app/github/1234/plan.md",
        "acme/billing-app/local/retry-exports/ticket.json",
        "acme/notes-app/product.json",
        "acme/notes-app/github/7/ticket.json",
        "personal/namespace.json",
        "personal/default/local/learn-rust/ticket.json",
    }


def test_the_manifest_names_the_scope_the_time_the_source_home_and_the_tickets(
    run_cli, home: Path, tmp_path: Path
):
    before = datetime.now(UTC).replace(microsecond=0)
    report = run_cli("archive", "export", cwd=tmp_path).json
    after = datetime.now(UTC)

    written = manifest(Path(report["archive"]))
    assert written["format"] == "sdlc-archive"
    assert written["version"] == 1
    assert written["scope"] == {"kind": "home", "ref": None}
    assert written["source_home"] == str(home.resolve())
    created = datetime.strptime(written["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    assert before <= created.replace(tzinfo=UTC) <= after
    assert written["tickets"] == [
        "acme/billing-app/github:1234",
        "acme/billing-app/local:retry-exports",
        "acme/notes-app/github:7",
        "personal/default/local:learn-rust",
    ]


def test_the_report_names_the_archive_its_scope_and_how_many_tickets_it_holds(
    run_cli, home: Path, tmp_path: Path
):
    report = run_cli("archive", "export", cwd=tmp_path).json

    assert report["scope"] == {"kind": "home", "ref": None}
    assert report["tickets"] == 4
    assert report["source_home"] == str(home.resolve())


def test_a_namespace_narrows_the_archive_to_it_and_the_home_config(
    run_cli, home: Path, tmp_path: Path
):
    report = run_cli("archive", "export", "acme", cwd=tmp_path).json

    archive = Path(report["archive"])
    assert entries(archive) == {
        "manifest.json",
        "sdlc.json",
        "acme/namespace.json",
        "acme/billing-app/product.json",
        "acme/billing-app/github/1234/ticket.json",
        "acme/billing-app/github/1234/raw/raw.json",
        "acme/billing-app/github/1234/journal/2026-11-20T10-00-00Z.md",
        "acme/billing-app/github/1234/plan.md",
        "acme/billing-app/local/retry-exports/ticket.json",
        "acme/notes-app/product.json",
        "acme/notes-app/github/7/ticket.json",
    }
    assert manifest(archive)["scope"] == {"kind": "namespace", "ref": "acme"}
    assert report["tickets"] == 3


def test_a_product_narrows_the_archive_to_it_and_the_config_above_it(
    run_cli, home: Path, tmp_path: Path
):
    report = run_cli("archive", "export", "acme/notes-app", cwd=tmp_path).json

    archive = Path(report["archive"])
    assert entries(archive) == {
        "manifest.json",
        "sdlc.json",
        "acme/namespace.json",
        "acme/notes-app/product.json",
        "acme/notes-app/github/7/ticket.json",
    }
    assert manifest(archive)["scope"] == {"kind": "product", "ref": "acme/notes-app"}
    assert manifest(archive)["tickets"] == ["acme/notes-app/github:7"]


@pytest.mark.parametrize(
    "reference", ["acme/billing-app/github:1234", "github:1234", "1234"]
)
def test_a_ticket_reference_narrows_the_archive_to_it_and_its_config(
    run_cli, home: Path, tmp_path: Path, reference: str
):
    report = run_cli("archive", "export", reference, cwd=tmp_path).json

    archive = Path(report["archive"])
    assert entries(archive) == {
        "manifest.json",
        "sdlc.json",
        "acme/namespace.json",
        "acme/billing-app/product.json",
        "acme/billing-app/github/1234/ticket.json",
        "acme/billing-app/github/1234/raw/raw.json",
        "acme/billing-app/github/1234/journal/2026-11-20T10-00-00Z.md",
        "acme/billing-app/github/1234/plan.md",
    }
    assert manifest(archive)["scope"] == {
        "kind": "ticket",
        "ref": "acme/billing-app/github:1234",
    }
    assert report["tickets"] == 1


@pytest.mark.parametrize(
    ("scope", "named"),
    [
        ("globex", "globex"),
        ("acme/payroll", "acme/payroll"),
        ("acme/billing-app/github:99", "acme/billing-app/github:99"),
    ],
)
def test_a_scope_that_is_not_in_the_home_is_an_error_and_writes_nothing(
    run_cli, home: Path, tmp_path: Path, scope: str, named: str
):
    result = run_cli("archive", "export", scope, cwd=tmp_path)

    assert result.code == 1
    assert named in result.err
    assert not list(tmp_path.glob("*.zip"))


def test_an_empty_home_is_an_error(run_cli, sdlc_home: Path, tmp_path: Path):
    result = run_cli("archive", "export", cwd=tmp_path)

    assert result.code == 1
    assert "SDLC home" in result.err
    assert not list(tmp_path.glob("*.zip"))


def test_a_name_that_is_both_a_namespace_and_a_ticket_is_ambiguous(
    run_cli, home: Path, make_ticket, tmp_path: Path
):
    make_ticket("personal", "default", "local", "acme")

    result = run_cli("archive", "export", "acme", cwd=tmp_path)

    assert result.code == 3
    assert "personal/default/local:acme" in result.err
    assert not list(tmp_path.glob("*.zip"))


@pytest.mark.parametrize(
    ("scope", "stem"),
    [
        (None, "sdlc-home"),
        ("acme", "sdlc-acme"),
        ("acme/billing-app", "sdlc-acme-billing-app"),
        ("github:1234", "sdlc-acme-billing-app-github-1234"),
    ],
)
def test_the_archive_is_named_after_its_scope_and_time_in_the_invocation_directory(
    run_cli, home: Path, tmp_path: Path, scope: str | None, stem: str
):
    report = run_cli(
        "archive", "export", *([scope] if scope else []), cwd=tmp_path
    ).json

    archive = Path(report["archive"])
    assert archive.parent == tmp_path
    assert re.fullmatch(rf"{stem}-\d{{4}}-\d\d-\d\dT\d\d-\d\d-\d\dZ\.zip", archive.name)


def test_out_names_the_zip_to_write(run_cli, home: Path, tmp_path: Path):
    target = tmp_path / "carry" / "acme.zip"
    target.parent.mkdir()

    report = run_cli(
        "archive", "export", "acme", "--out", str(target), cwd=tmp_path
    ).json

    assert report["archive"] == str(target)
    assert "acme/namespace.json" in entries(target)


def test_out_naming_a_directory_writes_the_named_zip_inside_it(
    run_cli, home: Path, tmp_path: Path
):
    folder = tmp_path / "carry"
    folder.mkdir()

    report = run_cli("archive", "export", "--out", str(folder), cwd=tmp_path).json

    archive = Path(report["archive"])
    assert archive.parent == folder
    assert archive.name.startswith("sdlc-home-")


def test_an_existing_zip_is_never_overwritten(run_cli, home: Path, tmp_path: Path):
    target = tmp_path / "acme.zip"
    target.write_bytes(b"mine")

    result = run_cli("archive", "export", "--out", str(target), cwd=tmp_path)

    assert result.code == 1
    assert str(target) in result.err
    assert target.read_bytes() == b"mine"


def test_an_archive_is_never_written_inside_the_sdlc_home(
    run_cli, home: Path, tmp_path: Path
):
    result = run_cli(
        "archive", "export", "--out", str(home / "acme" / "acme.zip"), cwd=tmp_path
    )

    assert result.code == 1
    assert "inside the SDLC home" in result.err
    assert not (home / "acme" / "acme.zip").exists()
