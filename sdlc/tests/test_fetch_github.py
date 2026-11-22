"""`fetch` mirrors a GitHub issue into raw/ through a stub `gh`: no network, no credentials."""

import json
from pathlib import Path

import pytest

TICKET = "acme/billing-app/github/1234"


@pytest.fixture
def bound(write_config):
    write_config("acme/namespace.json", {"sources": {"github": {"owner": "acme"}}})
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"github": {"repository": "billing-app"}}},
    )


def read(sdlc_home: Path, relative: str) -> dict:
    return json.loads((sdlc_home / relative).read_text(encoding="utf-8"))


def test_a_fetch_mirrors_the_issue_and_its_comments_under_the_bound_product(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue(
        comments=[{"id": 1, "body": "Which cache?"}, {"id": 2, "body": "Redis."}]
    )

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    assert result.json["product"] == "acme/billing-app"
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    assert raw["issue"]["title"] == "Cache the ledger lookup"
    assert raw["issue"]["labels"] == [{"name": "enhancement"}]
    assert [comment["body"] for comment in raw["comments"]] == [
        "Which cache?",
        "Redis.",
    ]


def test_a_fetch_records_what_the_source_determines_and_invents_no_type(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue()

    run_cli("fetch", "github:1234")

    record = read(sdlc_home, f"{TICKET}/ticket.json")
    assert record["source"] == "github"
    assert record["id"] == "1234"
    assert record["title"] == "Cache the ledger lookup"
    assert record["state"] == "open"
    assert record["url"] == "https://github.com/acme/billing-app/issues/1234"
    assert record["coordinates"] == {"owner": "acme", "repository": "billing-app"}
    assert record["last_fetched_at"].endswith("+00:00")
    assert "type" not in record


def test_the_mirror_holds_the_parent_the_sub_issues_and_the_blockers_with_their_state(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue(
        parent={"number": 1000, "title": "Billing revamp", "state": "open"},
        sub_issues=[{"number": 1235, "title": "Evict stale keys", "state": "closed"}],
        blocked_by=[{"number": 1100, "title": "Pick a cache", "state": "open"}],
        blocking=[{"number": 1300, "title": "Dashboard", "state": "open"}],
    )

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    assert raw["parent"]["number"] == 1000
    assert [(item["number"], item["state"]) for item in raw["sub_issues"]] == [
        (1235, "closed")
    ]
    assert [(item["number"], item["state"]) for item in raw["blocked_by"]] == [
        (1100, "open")
    ]
    assert [(item["number"], item["state"]) for item in raw["blocking"]] == [
        (1300, "open")
    ]
    assert result.json["fetched"]["relations"] == {
        "parent": True,
        "sub_issues": 1,
        "blocked_by": 1,
        "blocking": 1,
    }


def test_an_issue_without_a_parent_has_none_rather_than_an_error(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue()

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    assert read(sdlc_home, f"{TICKET}/raw/raw.json")["parent"] is None
    assert result.json["fetched"]["relations"]["parent"] is False


def test_coordinates_recorded_on_the_ticket_win_over_the_binding(
    run_cli, bound, stub_issue, gh_stub, make_ticket, write_config
):
    make_ticket("acme", "billing-app", "github", "1234")
    write_config(
        f"{TICKET}/ticket.json",
        {"coordinates": {"owner": "acme", "repository": "ledger"}},
    )
    stub_issue(repository="ledger", issue={"title": "From the ledger repository"})

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    assert gh_stub.asked_for("repos/acme/ledger/issues/1234")
    assert not gh_stub.asked_for("repos/acme/billing-app/issues/1234")
    assert result.json["product"] == "acme/billing-app"


def test_coordinates_given_on_the_command_line_file_the_ticket_under_the_namespace_default_product(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue(repository="ledger")

    result = run_cli(
        "fetch",
        "github:1234",
        "--coordinate",
        "owner=acme",
        "--coordinate",
        "repository=ledger",
    )

    assert result.code == 0, result.err
    assert result.json["product"] == "acme/default"
    record = read(sdlc_home, "acme/default/github/1234/ticket.json")
    assert record["coordinates"] == {"owner": "acme", "repository": "ledger"}


def test_the_same_number_in_another_repository_is_a_different_ticket(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue()
    stub_issue(repository="ledger", issue={"title": "Ledger's own 1234"})
    ledger = [
        "--coordinate",
        "owner=acme",
        "--coordinate",
        "repository=ledger",
    ]

    run_cli("fetch", "github:1234")
    result = run_cli("fetch", "github:1234", *ledger)

    assert result.code == 0, result.err
    assert result.json["product"] == "acme/default"
    assert (
        read(sdlc_home, f"{TICKET}/ticket.json")["title"] == "Cache the ledger lookup"
    )
    assert (
        read(sdlc_home, "acme/default/github/1234/ticket.json")["title"]
        == "Ledger's own 1234"
    )


def test_a_qualified_reference_files_the_ticket_under_the_named_product(
    run_cli, bound, stub_issue, write_config, sdlc_home
):
    write_config(
        "acme/ledger/product.json", {"sources": {"github": {"repository": "ledger"}}}
    )
    stub_issue(repository="ledger")

    result = run_cli("fetch", "acme/ledger/github:1234")

    assert result.code == 0, result.err
    assert (sdlc_home / "acme/ledger/github/1234/raw/raw.json").is_file()


def test_a_refresh_updates_the_mirror_and_keeps_the_recorded_type(
    run_cli, bound, stub_issue, gh_stub, sdlc_home
):
    stub_issue()
    run_cli("fetch", "github:1234")
    record_path = sdlc_home / TICKET / "ticket.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.update(type="spike", origin="notes/cache.md")
    record_path.write_text(json.dumps(record), encoding="utf-8")
    stub_issue(
        issue={"title": "Cache the ledger lookups", "state": "closed"},
        comments=[{"id": 7, "body": "Done."}],
    )

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    assert result.json["exists"] is True
    refreshed = read(sdlc_home, f"{TICKET}/ticket.json")
    assert refreshed["type"] == "spike"
    assert refreshed["origin"] == "notes/cache.md"
    assert refreshed["title"] == "Cache the ledger lookups"
    assert refreshed["state"] == "closed"
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    assert [comment["id"] for comment in raw["comments"]] == [7]


def fingerprint_after(run_cli, sdlc_home: Path) -> str:
    run_cli("fetch", "github:1234")
    return read(sdlc_home, f"{TICKET}/ticket.json")["fingerprint"]["sha256"]


def test_the_fingerprint_is_stable_while_nothing_the_mirror_holds_changed(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue(comments=[{"id": 1, "body": "Which cache?"}])

    first = fingerprint_after(run_cli, sdlc_home)
    second = fingerprint_after(run_cli, sdlc_home)

    assert first == second


@pytest.mark.parametrize(
    "change",
    [
        {"comments": [{"id": 1, "body": "Which cache?"}, {"id": 2, "body": "Redis."}]},
        {"comments": [{"id": 1, "body": "Which cache? (edited)"}]},
        {"issue": {"body": "Lookups are very slow."}},
        {"issue": {"labels": [{"name": "bug"}]}},
        {"parent": {"number": 1000, "title": "Billing revamp", "state": "open"}},
        {"blocked_by": [{"number": 1100, "title": "Pick a cache", "state": "open"}]},
    ],
    ids=["new comment", "edited comment", "body", "labels", "parent", "blocker"],
)
def test_the_fingerprint_changes_with_any_content_the_mirror_holds(
    run_cli, bound, stub_issue, sdlc_home, change
):
    stub_issue(comments=[{"id": 1, "body": "Which cache?"}])
    before = fingerprint_after(run_cli, sdlc_home)
    stub_issue(**{"comments": [{"id": 1, "body": "Which cache?"}], **change})

    after = fingerprint_after(run_cli, sdlc_home)

    assert after != before


def test_a_blocker_closing_changes_the_fingerprint(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue(blocked_by=[{"number": 1100, "title": "Pick a cache", "state": "open"}])
    before = fingerprint_after(run_cli, sdlc_home)
    stub_issue(
        blocked_by=[{"number": 1100, "title": "Pick a cache", "state": "closed"}]
    )

    assert fingerprint_after(run_cli, sdlc_home) != before


UUID = "0471ade0-320c-4e8a-9524-dd6664e50d14"
IMAGE_URL = f"https://github.com/user-attachments/assets/{UUID}"
FILE_URL = "https://github.com/user-attachments/files/9001/report.pdf"
PNG = b"\x89PNG\r\n\x1a\n" + b"pixels"
PDF = b"%PDF-1.7 report"


@pytest.fixture
def with_attachments(stub_issue, gh_stub):
    def register(**parts) -> None:
        stub_issue(
            issue={
                "body": f"Screenshot: ![image]({IMAGE_URL}) and see https://example.com/docs"
            },
            comments=[
                {"id": 5, "body": f"The [report.pdf]({FILE_URL}) has the numbers."}
            ],
            **parts,
        )
        gh_stub.respond_bytes(IMAGE_URL, PNG)
        gh_stub.respond_bytes(FILE_URL, PDF)

    return register


def test_every_attachment_in_the_body_and_the_comments_is_recorded_and_downloaded(
    run_cli, bound, with_attachments, sdlc_home
):
    with_attachments()

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    raw_dir = sdlc_home / TICKET / "raw"
    assert (raw_dir / f"{UUID}.png").read_bytes() == PNG
    assert (raw_dir / "9001-report.pdf").read_bytes() == PDF
    attachments = read(sdlc_home, f"{TICKET}/raw/raw.json")["attachments"]
    assert [(a["url"], a["name"], a["local_filename"]) for a in attachments] == [
        (IMAGE_URL, "image", f"{UUID}.png"),
        (FILE_URL, "report.pdf", "9001-report.pdf"),
    ]
    assert result.json["fetched"]["attachments"] == {
        "found": 2,
        "downloaded": 2,
        "kept": 0,
        "failed": [],
    }


def test_a_refresh_keeps_the_attachments_it_already_downloaded(
    run_cli, bound, with_attachments, gh_stub, sdlc_home
):
    with_attachments()
    run_cli("fetch", "github:1234")
    calls_before = len(gh_stub.calls)

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    downloads = [call for call in gh_stub.calls[calls_before:] if IMAGE_URL in call]
    assert downloads == []
    assert result.json["fetched"]["attachments"]["kept"] == 2
    assert result.json["fetched"]["attachments"]["downloaded"] == 0
    assert (sdlc_home / TICKET / "raw" / f"{UUID}.png").read_bytes() == PNG


def test_an_attachment_gh_cannot_download_is_recorded_and_reported_not_fatal(
    run_cli, bound, with_attachments, gh_stub, sdlc_home
):
    with_attachments()
    gh_stub.fail(IMAGE_URL, "gh: Not Found (HTTP 404)")

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    attachments = read(sdlc_home, f"{TICKET}/raw/raw.json")["attachments"]
    image = next(a for a in attachments if a["url"] == IMAGE_URL)
    assert image["local_filename"] is None
    failed = result.json["fetched"]["attachments"]["failed"]
    assert [item["url"] for item in failed] == [IMAGE_URL]
    assert "404" in failed[0]["error"]
    assert result.json["fetched"]["attachments"]["downloaded"] == 1


def test_ordinary_links_are_not_attachments(run_cli, bound, stub_issue, sdlc_home):
    stub_issue(
        issue={
            "body": "See https://example.com/a.png and https://github.com/acme/billing-app/pull/9"
        }
    )

    result = run_cli("fetch", "github:1234")

    assert read(sdlc_home, f"{TICKET}/raw/raw.json")["attachments"] == []
    assert result.json["fetched"]["attachments"]["found"] == 0


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/acme/billing-app/files/555/data.csv",
        "https://user-images.githubusercontent.com/1/pic.png",
    ],
)
def test_the_older_upload_urls_are_attachments_too(
    run_cli, bound, stub_issue, sdlc_home, url
):
    stub_issue(issue={"body": f"Attached: {url}."})

    result = run_cli("fetch", "github:1234")

    assert [
        a["url"] for a in read(sdlc_home, f"{TICKET}/raw/raw.json")["attachments"]
    ] == [url]
    assert result.json["fetched"]["attachments"]["failed"][0]["url"] == url


def test_an_issue_that_does_not_exist_is_not_found_and_writes_nothing(
    run_cli, bound, gh_stub, sdlc_home
):
    gh_stub.fail(
        "repos/acme/billing-app/issues/1234",
        "gh: Not Found (HTTP 404)",
    )

    result = run_cli("fetch", "github:1234")

    assert result.code == 5
    assert "repos/acme/billing-app/issues/1234" in result.err
    assert not (sdlc_home / TICKET).exists()


def test_a_gh_failure_part_way_leaves_no_partial_mirror(
    run_cli, bound, stub_issue, gh_stub, sdlc_home
):
    base = stub_issue()
    gh_stub.fail(f"{base}/dependencies/blocking", "gh: Server Error (HTTP 500)")

    result = run_cli("fetch", "github:1234")

    assert result.code == 1
    assert "HTTP 500" in result.err
    assert not (sdlc_home / TICKET).exists()


def test_a_connection_reset_is_retried_once(run_cli, bound, stub_issue, gh_stub):
    base = stub_issue()
    gh_stub.fail_then_respond(
        f"{base}/dependencies/blocked_by", "read: connection reset by peer", []
    )

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err


def test_not_being_signed_in_is_reported_before_any_request(
    run_cli, bound, stub_issue, gh_stub
):
    stub_issue()
    gh_stub.routes["auth status"] = {
        "stderr": "You are not logged into any GitHub hosts.",
        "code": 1,
    }
    gh_stub.save()

    result = run_cli("fetch", "github:1234")

    assert result.code == 1
    assert "not signed in to GitHub" in result.err
    assert "gh auth login" in result.err
    assert not gh_stub.asked_for("repos/acme/billing-app/issues/1234")


def test_a_missing_gh_is_reported_with_how_to_install_it(
    run_cli, bound, stub_issue, monkeypatch, tmp_path
):
    stub_issue()
    monkeypatch.setenv("PATH", str(tmp_path / "nowhere"))

    result = run_cli("fetch", "github:1234")

    assert result.code == 1
    assert "was not found on PATH" in result.err


def test_a_pull_request_number_is_not_an_issue(run_cli, bound, stub_issue, sdlc_home):
    stub_issue(issue={"pull_request": {"url": "https://api.github.com/pulls/1234"}})

    result = run_cli("fetch", "github:1234")

    assert result.code == 1
    assert "pull request" in result.err
    assert not (sdlc_home / TICKET).exists()


def test_a_repository_bound_nowhere_is_a_request_to_bind_it(run_cli, stub_issue):
    stub_issue()

    result = run_cli("fetch", "github:1234")

    assert result.code == 1
    assert "/sdlc:setup" in result.err


def test_a_bare_id_fetches_from_the_default_source(
    run_cli, bound, stub_issue, write_config, sdlc_home
):
    write_config("sdlc.json", {"default_source": "github"})
    stub_issue()

    result = run_cli("fetch", "1234")

    assert result.code == 0, result.err
    assert (sdlc_home / TICKET / "raw" / "raw.json").is_file()


def test_a_local_ticket_has_no_upstream_to_fetch(run_cli, make_ticket):
    make_ticket("acme", "billing-app", "local", "fix-login")

    result = run_cli("fetch", "local:fix-login")

    assert result.code == 1
    assert "no upstream" in result.err


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/user-attachments/assets/" + UUID,
        "https://github.com.evil.example/user-attachments/assets/" + UUID,
        "https://github.com@evil.example/user-attachments/assets/" + UUID,
        "https://github.com:8443/user-attachments/assets/" + UUID,
        "http://github.com/user-attachments/assets/" + UUID,
        "https://xuser-images.githubusercontent.com/1/pic.png",
        "https://user-images.githubusercontent.com.evil.example/1/pic.png",
    ],
)
def test_a_url_that_is_not_githubs_own_upload_host_is_no_attachment_and_never_sent_to_gh(
    run_cli, bound, stub_issue, gh_stub, sdlc_home, url
):
    stub_issue(comments=[{"id": 5, "body": f"Look: {url}"}])

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    assert read(sdlc_home, f"{TICKET}/raw/raw.json")["attachments"] == []
    assert not any(url in call for call in gh_stub.calls)
