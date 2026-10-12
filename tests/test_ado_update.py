import json

import pytest

pytestmark = pytest.mark.usefixtures("ado_bound")

REF = "contoso/big-project/ado:4242"


def work_item(rev=1, title="Export", state="Active", tags="", description="<p>old</p>", criteria="<p>ac</p>"):
    return {
        "id": 4242,
        "rev": rev,
        "fields": {
            "System.Title": title,
            "System.State": state,
            "System.WorkItemType": "User Story",
            "System.TeamProject": "Big Project",
            "System.Tags": tags,
            "System.Description": description,
            "Microsoft.VSTS.Common.AcceptanceCriteria": criteria,
        },
        "relations": [],
    }


class Upstream:
    """The work item as Azure DevOps holds it, changeable between calls."""

    def __init__(self, ado_stub):
        self.item = work_item(tags="billing; Spike")
        self.patches = []
        self.after_patch = None
        ado_stub.route("/_apis/wit/workItems/4242", lambda request: self.item)
        ado_stub.route("/comments", {"count": 0, "comments": []})
        ado_stub.route("/_apis/wit/workitems/4242", self.patch)

    def patch(self, request):
        self.patches.append(json.loads(request.data))
        if self.after_patch:
            self.item = self.after_patch()
        return self.item


@pytest.fixture
def upstream(run_cli, ado_stub):
    state = Upstream(ado_stub)
    assert run_cli("fetch", "ado:4242", "--in", "contoso/big-project").code == 0
    return state


def update(run_cli, *flags):
    return run_cli("update", REF, *flags)


def test_a_drifted_work_item_is_refused_with_the_instruction_to_refetch(run_cli, upstream):
    upstream.item = work_item(rev=2, title="Edited by someone else", tags="billing; Spike")

    result = update(run_cli, "--title", "Mine", "--confirm")

    assert result.code == 2
    assert "ticket-fetch" in result.err
    assert upstream.patches == []


def test_nothing_is_written_without_an_explicit_yes(run_cli, upstream):
    result = update(run_cli, "--title", "Export v2")

    assert result.code == 4
    assert upstream.patches == []


def test_the_diff_is_shown_and_nothing_is_written(run_cli, upstream):
    result = update(run_cli, "--title", "Export v2", "--state", "Resolved", "--propose")

    assert result.code == 0, result.err
    changes = {c["field"]: c for c in result.json["changes"]}
    assert changes["title"] == {"field": "title", "before": "Export", "after": "Export v2"}
    assert changes["state"]["after"] == "Resolved"
    assert upstream.patches == []


def test_each_updatable_field_is_written_as_a_json_patch_guarded_by_the_revision(
    run_cli, upstream, tmp_path
):
    description = tmp_path / "d.html"
    description.write_text("<p>new</p>", encoding="utf-8")
    criteria = tmp_path / "c.html"
    criteria.write_text("<p>new ac</p>", encoding="utf-8")

    result = update(
        run_cli,
        "--title", "Export v2",
        "--description-file", str(description),
        "--criteria-file", str(criteria),
        "--state", "Resolved",
        "--add-tag", "finance",
        "--remove-tag", "SPIKE",
        "--confirm",
    )

    assert result.code == 0, result.err
    patch = upstream.patches[0]
    assert patch[0] == {"op": "test", "path": "/rev", "value": 1}
    written = {op["path"]: op["value"] for op in patch[1:]}
    assert written == {
        "/fields/System.Title": "Export v2",
        "/fields/System.Description": "<p>new</p>",
        "/fields/Microsoft.VSTS.Common.AcceptanceCriteria": "<p>new ac</p>",
        "/fields/System.State": "Resolved",
        "/fields/System.Tags": "billing; finance",
    }


def test_only_changed_fields_are_written(run_cli, upstream):
    update(run_cli, "--title", "Export v2", "--confirm")

    paths = [op["path"] for op in upstream.patches[0][1:]]
    assert paths == ["/fields/System.Title"]


def test_an_update_with_no_changes_writes_nothing(run_cli, upstream):
    result = update(run_cli, "--title", "Export", "--confirm")

    assert result.code == 0
    assert result.json["changes"] == []
    assert upstream.patches == []


def test_the_snapshot_is_refetched_after_the_write(run_cli, upstream):
    upstream.after_patch = lambda: work_item(rev=2, title="Export v2", tags="billing; Spike")

    result = update(run_cli, "--title", "Export v2", "--confirm")

    assert result.code == 0, result.err
    assert result.json["written"] is True
    assert result.json["ticket_json"]["title"] == "Export v2"
    assert result.json["ticket_json"]["fingerprint"]["rev"] == 2


def test_a_source_without_the_capability_is_refused_as_a_gap(run_cli, local_ticket):
    assert run_cli("update", local_ticket()["ref"], "--propose").code == 3
