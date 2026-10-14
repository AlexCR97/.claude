from pathlib import Path

import pytest

LEGACY = """# Work Log — [#1: Hello](https://example.com/1)

> Newest entry first.

## 2026-10-11 09:30 UTC — Phase 2, Step 2.1

**Stopped at:** step 2.1

---

## 2026-10-10 16:05 UTC — Planning

**Stopped at:** planning

---

## 2026-10-10 16:05 UTC — Refinement

**Stopped at:** refinement
"""


@pytest.fixture
def ticket(local_ticket):
    return local_ticket()


def write_entry(run_cli, ticket, tmp_path, text="**Stopped at:** here", at=None):
    source = tmp_path / "entry.md"
    source.write_text(text, encoding="utf-8")
    args = ["journal", "write", ticket["ref"], "--file", str(source)]
    if at:
        args += ["--at", at]
    return run_cli(*args)


def journal_dir(ticket) -> Path:
    return Path(ticket["paths"]["ticket_dir"]) / "journal"


def test_a_checkpoint_creates_one_file_per_entry(run_cli, ticket, tmp_path):
    first = write_entry(run_cli, ticket, tmp_path, "one", "2026-10-11T09:30:00Z")
    second = write_entry(run_cli, ticket, tmp_path, "two", "2026-10-11T10:00:00Z")

    assert first.code == second.code == 0
    assert sorted(p.name for p in journal_dir(ticket).iterdir()) == [
        "2026-10-11T09-30-00Z.md",
        "2026-10-11T10-00-00Z.md",
    ]


def test_an_entry_name_is_safe_on_windows(run_cli, ticket, tmp_path):
    name = write_entry(run_cli, ticket, tmp_path).json["name"]

    assert not set(name) & set('<>:"/\|?*')


def test_a_same_second_collision_never_overwrites_and_keeps_the_order(
    run_cli, ticket, tmp_path
):
    write_entry(run_cli, ticket, tmp_path, "first", "2026-10-11T09:30:00Z")
    write_entry(run_cli, ticket, tmp_path, "second", "2026-10-11T09:30:00Z")

    names = sorted(p.name for p in journal_dir(ticket).iterdir())
    assert len(names) == 2
    texts = [(journal_dir(ticket) / n).read_text().strip() for n in names]
    assert texts == ["first", "second"]


def test_writing_never_modifies_an_existing_entry(run_cli, ticket, tmp_path):
    first = write_entry(run_cli, ticket, tmp_path, "keep me", "2026-10-11T09:30:00Z")
    path = Path(first.json["path"])
    before = path.read_bytes()

    write_entry(run_cli, ticket, tmp_path, "later", "2026-10-11T09:30:00Z")

    assert path.read_bytes() == before


def test_latest_reports_only_the_newest_entry(run_cli, ticket, tmp_path):
    write_entry(run_cli, ticket, tmp_path, "old", "2026-10-10T09:30:00Z")
    write_entry(run_cli, ticket, tmp_path, "new", "2026-10-11T09:30:00Z")

    latest = run_cli("journal", "latest", ticket["ref"]).json

    assert latest["path"].endswith("2026-10-11T09-30-00Z.md")
    assert latest["at"] == "2026-10-11T09:30:00+00:00"
    assert latest["entries"] == 2


def test_latest_on_a_ticket_with_no_journal_is_empty(run_cli, ticket):
    latest = run_cli("journal", "latest", ticket["ref"]).json

    assert latest["path"] is None
    assert latest["entries"] == 0


def test_older_entries_are_listed_on_request_newest_first(run_cli, ticket, tmp_path):
    write_entry(run_cli, ticket, tmp_path, "old", "2026-10-10T09:30:00Z")
    write_entry(run_cli, ticket, tmp_path, "new", "2026-10-11T09:30:00Z")

    listed = run_cli("journal", "list", ticket["ref"]).json["entries"]

    assert [e["at"][:10] for e in listed] == ["2026-10-11", "2026-10-10"]


def test_an_empty_entry_is_refused(run_cli, ticket, tmp_path):
    result = write_entry(run_cli, ticket, tmp_path, "   \n")

    assert result.code != 0
    assert not journal_dir(ticket).exists()


def test_migration_splits_a_journal_into_entries_named_from_their_headings(
    run_cli, ticket
):
    ticket_dir = Path(ticket["paths"]["ticket_dir"])
    (ticket_dir / "journal.md").write_text(LEGACY, encoding="utf-8")

    result = run_cli("journal", "migrate", ticket["ref"])

    assert result.code == 0, result.err
    names = sorted(p.name for p in journal_dir(ticket).iterdir())
    assert names[0] == "2026-10-10T16-05-00Z.md"
    assert names[1] == "2026-10-10T16-05-01Z.md"
    assert names[2] == "2026-10-11T09-30-00Z.md"
    contents = [(journal_dir(ticket) / n).read_text() for n in names]
    assert "Refinement" in contents[0] and "Planning" in contents[1]
    assert all(not c.rstrip().endswith("---") for c in contents)


def test_migration_keeps_the_original_as_a_backup(run_cli, ticket):
    ticket_dir = Path(ticket["paths"]["ticket_dir"])
    (ticket_dir / "journal.md").write_text(LEGACY, encoding="utf-8")

    backup = Path(run_cli("journal", "migrate", ticket["ref"]).json["backup"])

    assert backup.read_text(encoding="utf-8") == LEGACY
    assert not (ticket_dir / "journal.md").exists()


def test_migrating_without_a_journal_is_refused(run_cli, ticket):
    assert run_cli("journal", "migrate", ticket["ref"]).code != 0


def test_listings_report_the_newest_entry_date(run_cli, ticket, tmp_path):
    write_entry(run_cli, ticket, tmp_path, "new", "2026-10-11T09:30:00Z")

    listed = run_cli("list").json

    entry = next(e for e in listed["tickets"] if e["id"] == ticket["id"])
    assert entry["has_journal"] is True
    assert entry["last_journal_entry"] == "2026-10-11T09:30:00+00:00"


def test_resolve_requires_a_journal_through_the_directory(run_cli, ticket, tmp_path):
    assert run_cli("resolve", ticket["ref"], "--require", "journal").code == 2

    write_entry(run_cli, ticket, tmp_path)

    assert run_cli("resolve", ticket["ref"], "--require", "journal").code == 0
