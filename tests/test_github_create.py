import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("github_bound")


def issue_payload(number, title="Export invoices", labels=("enhancement",)):
    return json.dumps(
        {
            "number": number,
            "title": title,
            "state": "open",
            "body": "body",
            "html_url": f"https://github.com/acme/web/issues/{number}",
            "updated_at": "2026-10-11T10:00:00Z",
            "labels": [{"name": name} for name in labels],
        }
    )


@pytest.fixture
def stubbed(gh_stub):
    gh_stub.respond("-X POST", issue_payload(77))
    gh_stub.respond("issues/77/comments", "[]")
    gh_stub.respond("repos/acme/web/issues/77", issue_payload(77))
    return gh_stub


def create(run_cli, *extra, tail=("--confirm",)):
    return run_cli(
        "new", "--source", "github", "--title", "Export invoices", "--type", "user-story",
        *extra, *tail,
    )


def test_proposing_shows_everything_and_writes_nothing(run_cli, stubbed, tmp_path):
    body = tmp_path / "body.md"
    body.write_text("As a user I want exports.", encoding="utf-8")
    criteria = tmp_path / "criteria.md"
    criteria.write_text("- [ ] a CSV downloads", encoding="utf-8")

    result = create(
        run_cli, "--body-file", str(body), "--criteria-file", str(criteria),
        "--label", "billing", tail=("--propose",),
    )

    assert result.code == 0, result.err
    shown = result.json
    assert shown["confirmation_required"] is True
    assert shown["product"] == "acme/web"
    proposal = shown["proposal"]
    assert (proposal["title"], proposal["type"]) == ("Export invoices", "user-story")
    assert proposal["labels"] == ["billing", "enhancement"]
    assert "As a user I want exports." in proposal["body"]
    assert "## Acceptance Criteria" in proposal["body"]
    assert stubbed.sent("-X POST") == []


def test_nothing_is_created_without_an_explicit_confirmation(run_cli, stubbed):
    result = create(run_cli, tail=())

    assert result.code == 4
    assert "confirmation" in result.err
    assert stubbed.sent("-X POST") == []
    assert not any("POST" in " ".join(call) for call in stubbed.calls)


def test_a_confirmed_create_sends_the_proposal_and_labels(run_cli, stubbed, tmp_path):
    body = tmp_path / "body.md"
    body.write_text("Details", encoding="utf-8")

    result = create(run_cli, "--body-file", str(body), "--label", "billing")

    assert result.code == 0, result.err
    sent = stubbed.sent("-X POST")[0]
    assert sent["title"] == "Export invoices"
    assert sent["body"] == "Details"
    assert sent["labels"] == ["billing", "enhancement"]


def test_the_created_issue_is_fetched_and_filed_under_its_real_number(
    run_cli, stubbed
):
    result = create(run_cli)

    report = result.json
    assert report["id"] == "77"
    assert report["qualified_ref"] == "acme/web/github:77"
    ticket_dir = Path(report["paths"]["ticket_dir"])
    assert ticket_dir.name == "77"
    assert (ticket_dir / "raw" / "raw.json").is_file()
    assert report["ticket_json"]["url"] == "https://github.com/acme/web/issues/77"


def test_the_type_is_recorded_in_the_ticket(run_cli, stubbed):
    record = create(run_cli).json["ticket_json"]

    assert record["type"] == "user-story"


@pytest.mark.parametrize(
    ("ticket_type", "label"),
    [("bug", "bug"), ("spike", "spike"), ("tech-debt", "tech-debt"), ("user-story", "enhancement")],
)
def test_the_canonical_type_is_applied_as_its_native_label(
    run_cli, stubbed, ticket_type, label
):
    run_cli(
        "new", "--source", "github", "--title", "T", "--type", ticket_type, "--confirm"
    )

    assert label in stubbed.sent("-X POST")[0]["labels"]


def test_a_task_is_created_unlabelled(run_cli, stubbed):
    run_cli("new", "--source", "github", "--title", "T", "--type", "task", "--confirm")

    assert stubbed.sent("-X POST")[0]["labels"] == []


def test_a_type_is_required(run_cli, stubbed):
    result = run_cli("new", "--source", "github", "--title", "T", "--confirm")

    assert result.code == 1
    assert "--type" in result.err


def test_a_source_without_the_capability_is_still_refused(run_cli, monkeypatch):
    from ticketlib import providers

    monkeypatch.setattr(providers, "capabilities", lambda source: {"fetch": True, "new": False})

    result = run_cli("new", "--source", "github", "--title", "T", "--type", "task", "--confirm")

    assert result.code == 3
