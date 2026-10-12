import json

import pytest

pytestmark = pytest.mark.usefixtures("ado_bound")

AGILE = ["Epic", "Feature", "User Story", "Task", "Bug", "Issue"]
SCRUM = ["Epic", "Feature", "Product Backlog Item", "Task", "Bug", "Impediment"]


def work_item(item_id, native="User Story", tags="", parent=None):
    relations = []
    if parent:
        relations.append(
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"https://dev.azure.com/contoso/_apis/wit/workItems/{parent}",
            }
        )
    return {
        "id": item_id,
        "rev": 1,
        "fields": {
            "System.Title": "Export invoices",
            "System.State": "New",
            "System.WorkItemType": native,
            "System.TeamProject": "Big Project",
            "System.Tags": tags,
        },
        "relations": relations,
    }


@pytest.fixture
def stubbed(ado_stub):
    created = {}

    def create(request):
        created["operations"] = json.loads(request.data)
        created["content_type"] = request.get_header("Content-type")
        created["url"] = request.full_url
        return {"id": 4300}

    ado_stub.created = created
    ado_stub.route("/_apis/wit/workItems/4300", work_item(4300))
    ado_stub.route("/comments", {"count": 0, "comments": []})
    ado_stub.route("/_apis/wit/workitems/$", create)
    ado_stub.route("/_apis/wit/workitemtypes", {"value": [{"name": n} for n in AGILE]})
    return ado_stub


def create(run_cli, ticket_type="user-story", *extra, tail=("--confirm",)):
    return run_cli(
        "new", "--source", "ado", "--title", "Export invoices", "--type", ticket_type,
        *extra, *tail,
    )


def test_nothing_is_created_without_an_explicit_confirmation(run_cli, stubbed):
    result = create(run_cli, tail=())

    assert result.code == 4
    assert not any(method == "POST" for method, _ in stubbed.requests)


def test_proposing_reads_the_project_and_writes_nothing(run_cli, stubbed, tmp_path):
    criteria = tmp_path / "ac.html"
    criteria.write_text("<ul><li>CSV downloads</li></ul>", encoding="utf-8")

    result = create(run_cli, "user-story", "--criteria-file", str(criteria), tail=("--propose",))

    assert result.code == 0, result.err
    proposal = result.json["proposal"]
    assert proposal["native_type"] == "User Story"
    assert proposal["acceptance_criteria"].startswith("<ul>")
    assert result.json["product"] == "contoso/big-project"
    assert not any(method == "POST" for method, _ in stubbed.requests)


@pytest.mark.parametrize(
    ("template", "canonical", "native"),
    [
        (AGILE, "user-story", "User Story"),
        (SCRUM, "user-story", "Product Backlog Item"),
        (AGILE, "bug", "Bug"),
        (AGILE, "task", "Task"),
        (AGILE, "spike", "Task"),
        (SCRUM, "tech-debt", "Task"),
    ],
)
def test_the_canonical_type_maps_to_the_projects_native_type(
    run_cli, ado_stub, template, canonical, native
):
    ado_stub.route("/_apis/wit/workitemtypes", {"value": [{"name": n} for n in template]})

    proposal = create(run_cli, canonical, tail=("--propose",)).json["proposal"]

    assert proposal["native_type"] == native


def test_spikes_and_tech_debt_are_told_apart_by_a_tag(run_cli, stubbed):
    proposal = create(run_cli, "spike", "--tag", "billing", tail=("--propose",)).json["proposal"]

    assert proposal["labels"] == ["billing", "spike"]


def test_a_project_with_no_matching_type_is_an_error_listing_its_types(run_cli, ado_stub):
    ado_stub.route("/_apis/wit/workitemtypes", {"value": [{"name": "Impediment"}]})

    result = create(run_cli, "bug", tail=("--propose",))

    assert result.code == 1
    assert "Impediment" in result.err


def test_the_created_work_item_is_posted_as_a_json_patch_to_its_native_type(
    run_cli, stubbed, tmp_path
):
    body = tmp_path / "body.html"
    body.write_text("<p>Details</p>", encoding="utf-8")

    result = create(run_cli, "user-story", "--body-file", str(body))

    assert result.code == 0, result.err
    assert "/workitems/$User%20Story" in stubbed.created["url"]
    assert stubbed.created["content_type"] == "application/json-patch+json"
    fields = {op["path"]: op["value"] for op in stubbed.created["operations"]}
    assert fields["/fields/System.Title"] == "Export invoices"
    assert fields["/fields/System.Description"] == "<p>Details</p>"


def test_the_created_work_item_is_fetched_and_filed_under_its_real_id(run_cli, stubbed):
    report = create(run_cli).json

    assert report["id"] == "4300"
    assert report["qualified_ref"] == "contoso/big-project/ado:4300"
    assert report["ticket_json"]["url"] == (
        "https://dev.azure.com/contoso/Big%20Project/_workitems/edit/4300"
    )
    assert report["ticket_json"]["type"] == "user-story"


def test_a_task_created_with_a_parent_is_linked_upstream_and_locally(
    run_cli, ado_stub, stubbed
):
    ado_stub.route("/_apis/wit/workItems/4300", work_item(4300, "Task", parent=4200))
    ado_stub.route("/_apis/wit/workItems/4200", work_item(4200))

    report = create(run_cli, "task", "--parent", "ado:4200").json

    relations = [op for op in stubbed.created["operations"] if op["path"] == "/relations/-"]
    assert relations[0]["value"]["rel"] == "System.LinkTypes.Hierarchy-Reverse"
    assert relations[0]["value"]["url"].endswith("/workItems/4200")
    assert report["ticket_json"]["parent"] == "ado:4200"


def test_a_parent_on_anything_but_a_task_is_refused_before_writing(run_cli, stubbed):
    result = create(run_cli, "bug", "--parent", "4200")

    assert result.code == 1
    assert not any(method == "POST" for method, _ in stubbed.requests)


def test_a_parent_that_is_not_an_id_is_refused(run_cli, stubbed):
    assert create(run_cli, "task", "--parent", "the-story").code == 1
