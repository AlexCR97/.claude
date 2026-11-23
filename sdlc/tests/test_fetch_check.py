"""`fetch --check` compares a mirrored ticket's recorded revision with the live one and writes nothing."""

import hashlib
from pathlib import Path

import pytest

GITHUB = "acme/billing-app/github/1234"
ADO_BOTH = ["--coordinate", "organization=acme", "--coordinate", "project=billing-app"]


@pytest.fixture
def bound(write_config):
    write_config(
        "acme/namespace.json",
        {"sources": {"github": {"owner": "acme"}, "ado": {"organization": "acme"}}},
    )
    write_config(
        "acme/billing-app/product.json",
        {
            "sources": {
                "github": {"repository": "billing-app"},
                "ado": {"project": "billing-app"},
            }
        },
    )


def tree_state(root: Path) -> dict[str, str]:
    """Every file under `root` and every directory, so a stray write of either shows."""
    return {
        str(path.relative_to(root)): (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "dir"
        )
        for path in sorted(root.rglob("*"))
    }


def test_a_github_issue_whose_content_is_unchanged_reports_unchanged_with_both_fingerprints(
    run_cli, bound, stub_issue
):
    stub_issue()
    run_cli("fetch", "github:1234")

    result = run_cli("fetch", "github:1234", "--check")

    assert result.code == 0, result.err
    report = result.json
    assert report["changed"] is False
    assert report["status"] == "unchanged"
    assert report["recorded"] == report["live"]
    assert len(report["live"]["sha256"]) == 64


def test_a_github_issue_edited_upstream_reports_changed_and_the_fingerprints_differ(
    run_cli, bound, stub_issue
):
    stub_issue()
    run_cli("fetch", "github:1234")
    stub_issue(comments=[{"id": 9, "body": "Use Redis."}])

    result = run_cli("fetch", "github:1234", "--check")

    assert result.code == 0, result.err
    assert result.json["changed"] is True
    assert result.json["status"] == "changed"
    assert result.json["recorded"] != result.json["live"]


def test_a_check_writes_nothing_even_when_the_issue_holds_an_attachment_a_fetch_would_download(
    run_cli, bound, stub_issue, gh_stub, sdlc_home
):
    stub_issue()
    run_cli("fetch", "github:1234")
    url = "https://github.com/user-attachments/assets/0f0f0f0f-0000-4000-8000-000000000001"
    stub_issue(issue={"body": f"See ![shot]({url})"})
    gh_stub.respond_bytes(url, b"\x89PNG....")
    before = tree_state(sdlc_home)

    result = run_cli("fetch", "github:1234", "--check")

    assert result.json["changed"] is True
    assert tree_state(sdlc_home) == before
    assert not gh_stub.asked_for(url)


def test_a_ticket_never_mirrored_says_so_and_nothing_is_created(
    run_cli, bound, sdlc_home, stub_issue
):
    stub_issue()

    result = run_cli("fetch", "github:1234", "--check")

    assert result.code == 0, result.err
    report = result.json
    assert report["status"] == "never_mirrored"
    assert report["changed"] is True
    assert report["recorded"] is None
    assert "never been fetched" in report["reason"]
    assert not sdlc_home.exists() or not (sdlc_home / GITHUB).exists()


def test_a_ticket_on_disk_without_a_recorded_revision_counts_as_never_mirrored(
    run_cli, bound, make_ticket, write_config, stub_issue
):
    make_ticket("acme", "billing-app", "github", "1234")
    write_config(f"{GITHUB}/ticket.json", {"source": "github", "id": "1234"})
    stub_issue()

    result = run_cli("fetch", "github:1234", "--check")

    assert result.json["status"] == "never_mirrored"


def test_a_local_ticket_has_nothing_upstream_and_never_changes(
    run_cli, bound, make_ticket, write_config
):
    make_ticket("acme", "billing-app", "local", "cache-ledger")
    write_config(
        "acme/billing-app/local/cache-ledger/ticket.json",
        {"source": "local", "id": "cache-ledger"},
    )

    result = run_cli("fetch", "local:cache-ledger", "--check")

    assert result.code == 0, result.err
    assert result.json["changed"] is False
    assert result.json["status"] == "local"
    assert "no upstream" in result.json["reason"]


def test_an_upstream_failure_is_reported_as_fetch_reports_it_and_nothing_is_written(
    run_cli, bound, stub_issue, gh_stub, sdlc_home
):
    stub_issue()
    run_cli("fetch", "github:1234")
    base = stub_issue()
    gh_stub.fail(f"{base}/comments", "gh: HTTP 500")
    before = tree_state(sdlc_home)

    result = run_cli("fetch", "github:1234", "--check")

    assert result.code == 1
    assert "HTTP 500" in result.err
    assert tree_state(sdlc_home) == before


def test_a_missing_issue_exits_not_found(run_cli, bound, stub_issue, gh_stub):
    base = stub_issue()
    run_cli("fetch", "github:1234")
    gh_stub.fail(base, "gh: Not Found (HTTP 404)")

    result = run_cli("fetch", "github:1234", "--check")

    assert result.code == 5


@pytest.fixture
def mirrored_work_item(run_cli, bound, az_stub):
    base = "https://dev.azure.com/acme"
    item = f"{base}/_apis/wit/workItems/1234"
    az_stub.respond(
        f"{item}?$expand=all",
        {
            "id": 1234,
            "rev": 7,
            "fields": {
                "System.WorkItemType": "User Story",
                "System.TeamProject": "billing-app",
                "System.Title": "Cache the ledger lookup",
                "System.State": "Active",
            },
        },
    )
    az_stub.respond(
        f"{base}/billing-app/_apis/wit/workItems/1234/comments", {"comments": []}
    )
    assert run_cli("fetch", "ado:1234", *ADO_BOTH).code == 0
    return item


def probe(az_stub, item: str, rev: int) -> None:
    az_stub.respond(
        f"{item}?fields=System.Rev",
        {"id": 1234, "rev": rev, "fields": {"System.Rev": rev}},
    )


def test_a_work_item_at_the_recorded_rev_reports_unchanged(
    run_cli, mirrored_work_item, az_stub
):
    probe(az_stub, mirrored_work_item, 7)

    result = run_cli("fetch", "ado:1234", "--check")

    assert result.code == 0, result.err
    assert result.json["changed"] is False
    assert result.json["recorded"] == {"rev": 7}
    assert result.json["live"] == {"rev": 7}


def test_a_work_item_at_a_newer_rev_reports_changed(
    run_cli, mirrored_work_item, az_stub
):
    probe(az_stub, mirrored_work_item, 9)

    result = run_cli("fetch", "ado:1234", "--check")

    assert result.json["changed"] is True
    assert result.json["live"] == {"rev": 9}


def test_the_work_item_check_at_the_recorded_rev_asks_only_for_the_revision(
    run_cli, mirrored_work_item, az_stub, sdlc_home
):
    probe(az_stub, mirrored_work_item, 7)
    before = tree_state(sdlc_home)
    calls_before = len(az_stub.calls)

    run_cli("fetch", "ado:1234", "--check")

    new_calls = az_stub.calls[calls_before:]
    assert len(new_calls) == 1
    assert "fields=System.Rev" in " ".join(new_calls[0])
    assert tree_state(sdlc_home) == before


def test_the_work_item_check_at_a_newer_rev_reads_the_item_and_its_comments_and_writes_nothing(
    run_cli, mirrored_work_item, az_stub, sdlc_home
):
    probe(az_stub, mirrored_work_item, 9)
    before = tree_state(sdlc_home)
    calls_before = len(az_stub.calls)

    run_cli("fetch", "ado:1234", "--check")

    new_calls = [" ".join(call) for call in az_stub.calls[calls_before:]]
    assert len(new_calls) == 3
    assert "fields=System.Rev" in new_calls[0]
    assert "$expand=all" in new_calls[1]
    assert "/comments" in new_calls[2]
    assert tree_state(sdlc_home) == before


def test_a_work_item_that_cannot_be_read_fails_with_nothing_written(
    run_cli, mirrored_work_item, az_stub, sdlc_home
):
    az_stub.fail(f"{mirrored_work_item}?fields=System.Rev", "TF401232: Not Found")
    before = tree_state(sdlc_home)

    result = run_cli("fetch", "ado:1234", "--check")

    assert result.code == 5
    assert tree_state(sdlc_home) == before


@pytest.mark.parametrize(
    ("source", "recorded", "arguments"),
    [("github", {"sha256": "ab" * 32}, []), ("ado", {"rev": 7}, ADO_BOTH)],
)
def test_a_remote_ticket_with_an_old_shape_mirror_is_stale_not_unchanged(
    run_cli,
    bound,
    make_ticket,
    write_config,
    gh_stub,
    az_stub,
    source,
    recorded,
    arguments,
):
    directory = make_ticket("acme", "billing-app", source, "1234")
    (directory / "raw").mkdir()
    (directory / "raw" / "workitem.json").write_text("{}", encoding="utf-8")
    write_config(
        f"acme/billing-app/{source}/1234/ticket.json",
        {"source": source, "id": "1234", "fingerprint": recorded},
    )

    result = run_cli("fetch", f"{source}:1234", "--check", *arguments)

    assert result.code == 0, result.err
    assert result.json["status"] == "stale_mirror"
    assert result.json["changed"] is True
    assert result.json["recorded"] == recorded
    assert "/sdlc:intake" in result.json["reason"]
    assert gh_stub.calls == [] and az_stub.calls == []
