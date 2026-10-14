import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("github_bound")

BODY = (
    "Original description.\n\n## Acceptance Criteria\n\n- [ ] old criterion\n\n"
    "## Notes\n\nKeep me."
)


def issue(number=7, title="Export", state="open", labels=("enhancement",), body=BODY, updated="T1"):
    return json.dumps(
        {
            "number": number,
            "title": title,
            "state": state,
            "body": body,
            "html_url": f"https://github.com/acme/web/issues/{number}",
            "updated_at": updated,
            "labels": [{"name": name} for name in labels],
        }
    )


@pytest.fixture
def fetched(run_cli, gh_stub):
    gh_stub.respond("issues/7/comments", "[]")
    gh_stub.respond("repos/acme/web/issues/7", issue())
    assert run_cli("fetch", "github:7").code == 0
    return gh_stub


def update(run_cli, *flags):
    return run_cli("update", "acme/web/github:7", *flags)


def test_a_drifted_issue_is_refused_with_the_instruction_to_refetch(run_cli, fetched):
    fetched.respond("repos/acme/web/issues/7", issue(updated="T2"))

    result = update(run_cli, "--title", "New", "--confirm")

    assert result.code == 2
    assert "ticket-fetch" in result.err
    assert fetched.sent("PATCH") == []


def test_the_diff_is_shown_and_nothing_is_written(run_cli, fetched):
    result = update(run_cli, "--title", "Export v2", "--state", "closed", "--propose")

    assert result.code == 0, result.err
    changes = {c["field"]: c for c in result.json["changes"]}
    assert changes["title"]["before"] == "Export"
    assert changes["title"]["after"] == "Export v2"
    assert changes["state"]["after"] == "closed"
    assert result.json["written"] is False
    assert fetched.sent("PATCH") == []


def test_nothing_is_written_without_an_explicit_yes(run_cli, fetched):
    result = update(run_cli, "--title", "Export v2")

    assert result.code == 4
    assert fetched.sent("PATCH") == []


def test_an_update_with_no_changes_writes_nothing(run_cli, fetched):
    result = update(run_cli, "--title", "Export", "--confirm")

    assert result.code == 0
    assert result.json["changes"] == []
    assert fetched.sent("PATCH") == []


def test_title_and_state_are_written(run_cli, fetched):
    update(run_cli, "--title", "Export v2", "--state", "closed", "--confirm")

    sent = fetched.sent("PATCH")[0]
    assert sent == {"title": "Export v2", "state": "closed"}


def test_labels_are_added_and_removed_case_insensitively(run_cli, fetched):
    update(run_cli, "--add-label", "billing", "--remove-label", "ENHANCEMENT", "--confirm")

    assert fetched.sent("PATCH")[0] == {"labels": ["billing"]}


def test_the_description_changes_and_the_criteria_and_notes_are_kept(
    run_cli, fetched, tmp_path
):
    description = tmp_path / "d.md"
    description.write_text("A better description.", encoding="utf-8")

    update(run_cli, "--description-file", str(description), "--confirm")

    body = fetched.sent("PATCH")[0]["body"]
    assert body.startswith("A better description.")
    assert "- [ ] old criterion" in body
    assert "## Notes\n\nKeep me." in body


def test_the_acceptance_criteria_change_and_the_rest_is_kept(run_cli, fetched, tmp_path):
    criteria = tmp_path / "c.md"
    criteria.write_text("- [ ] new criterion", encoding="utf-8")

    update(run_cli, "--criteria-file", str(criteria), "--confirm")

    body = fetched.sent("PATCH")[0]["body"]
    assert body.startswith("Original description.")
    assert "- [ ] new criterion" in body
    assert "old criterion" not in body
    assert body.endswith("## Notes\n\nKeep me.")


def test_criteria_are_added_when_the_body_has_none(run_cli, gh_stub, tmp_path):
    gh_stub.respond("issues/7/comments", "[]")
    gh_stub.respond("repos/acme/web/issues/7", issue(body="Just text."))
    run_cli("fetch", "github:7")
    criteria = tmp_path / "c.md"
    criteria.write_text("- [ ] first", encoding="utf-8")

    update(run_cli, "--criteria-file", str(criteria), "--confirm")

    assert gh_stub.sent("PATCH")[0]["body"] == "Just text.\n\n## Acceptance Criteria\n\n- [ ] first"


def test_the_snapshot_is_refetched_after_the_write(run_cli, fetched):
    # The drift check and the proposal each read the issue before the write; the re-fetch is the next call.
    fetched.respond_in_turn(
        "-X PATCH", issue(title="Export v2", updated="T2")
    )
    fetched.respond_in_turn(
        "repos/acme/web/issues/7", issue(), issue(title="Export v2", updated="T2")
    )

    result = update(run_cli, "--title", "Export v2", "--confirm")

    assert result.code == 0, result.err
    assert result.json["written"] is True
    assert result.json["ticket_json"]["title"] == "Export v2"
    raw = json.loads(Path(result.json["fetched"]["raw_json"]).read_text(encoding="utf-8"))
    assert raw["issue"]["updated_at"] == "T2"


def test_a_source_without_the_capability_is_refused_as_a_gap(run_cli, local_ticket):
    ticket = local_ticket()

    result = run_cli("update", ticket["ref"], "--propose")

    assert result.code == 3
