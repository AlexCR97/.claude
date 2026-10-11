import json
from pathlib import Path

import pytest

CANONICAL = "https://dev.azure.com/contoso/Big%20Project/_workitems/edit/4242"


def prepare(run_cli, ref):
    result = run_cli("prepare", ref)
    assert result.code == 0, result.err
    return result.json


def test_a_local_ticket_with_no_digest_is_digested_without_a_fetch(run_cli, local_ticket):
    ticket = local_ticket()

    report = prepare(run_cli, ticket["ref"])

    assert report["steps"] == ["digest"]


def test_a_local_ticket_with_a_digest_and_no_drift_needs_nothing(run_cli, local_ticket):
    ticket = local_ticket()
    (Path(ticket["paths"]["ticket_dir"]) / "digest.md").write_text("# d", encoding="utf-8")

    report = prepare(run_cli, ticket["ref"])

    assert report["steps"] == []
    assert report["ask_before_refresh"] is False


def test_a_drifted_local_ticket_asks_before_refreshing(run_cli, local_ticket):
    ticket = local_ticket()
    ticket_dir = Path(ticket["paths"]["ticket_dir"])
    (ticket_dir / "digest.md").write_text("# d", encoding="utf-8")
    data = json.loads((ticket_dir / "ticket.json").read_text(encoding="utf-8"))
    data["fingerprint"] = {"sha256": "stale"}
    (ticket_dir / "ticket.json").write_text(json.dumps(data), encoding="utf-8")

    report = prepare(run_cli, ticket["ref"])

    assert report["ask_before_refresh"] is True
    assert report["refresh_steps"] == ["digest"]


@pytest.mark.usefixtures("ado_bound")
def test_a_pasted_address_for_a_ticket_not_on_disk_starts_with_a_fetch(run_cli):
    report = prepare(run_cli, CANONICAL)

    assert report["filed"] is False
    assert report["steps"] == ["fetch", "digest"]


@pytest.mark.usefixtures("ado_bound")
def test_a_fetched_ticket_with_no_digest_only_needs_digesting(run_cli, ado_stub):
    ado_stub.route(
        "/_apis/wit/workItems/4242",
        {
            "id": 4242,
            "rev": 1,
            "fields": {
                "System.Title": "Export",
                "System.State": "New",
                "System.WorkItemType": "Task",
                "System.TeamProject": "Big Project",
            },
            "relations": [],
        },
    )
    ado_stub.route("/comments", {"count": 0, "comments": []})
    assert run_cli("fetch", CANONICAL).code == 0

    report = prepare(run_cli, CANONICAL)

    assert report["filed"] is True
    assert report["steps"] == ["digest"]
