import pytest

pytestmark = pytest.mark.usefixtures("ado_bound")

CANONICAL = "https://dev.azure.com/contoso/Big%20Project/_workitems/edit/4242"

FORMS = [
    "https://dev.azure.com/contoso/Big%20Project/_workitems/edit/4242",
    "https://contoso.visualstudio.com/Big%20Project/_workitems/edit/4242",
    "http://dev.azure.com/contoso/Big%20Project/_workitems/edit/4242",
    "http://contoso.visualstudio.com/Big%20Project/_workitems/edit/4242",
    "https://dev.azure.com/contoso/Big%20Project/_workitems/edit/4242?view=board",
    "https://contoso.visualstudio.com/Big%20Project/_workitems/edit/4242#discussion",
    "https://contoso.visualstudio.com/Big%20Project/_workitems/edit/4242/",
]


@pytest.mark.parametrize("address", FORMS)
def test_every_address_form_resolves_to_the_same_ticket(run_cli, address):
    result = run_cli("resolve", address)

    assert result.code == 0, result.err
    resolved = result.json
    assert resolved["source"] == "ado"
    assert resolved["id"] == "4242"
    assert resolved["coordinates"]["organization"] == "contoso"
    assert resolved["coordinates"]["project"] == "Big Project"


@pytest.mark.parametrize("address", FORMS)
def test_a_pasted_address_is_reported_under_the_canonical_url(run_cli, address):
    resolved = run_cli("resolve", address).json

    assert resolved["url"] == CANONICAL


def test_an_unencoded_project_is_accepted(run_cli):
    resolved = run_cli(
        "resolve", "https://contoso.visualstudio.com/Big Project/_workitems/edit/7"
    ).json

    assert resolved["coordinates"]["project"] == "Big Project"


def test_a_visualstudio_address_with_no_work_item_is_refused(run_cli):
    result = run_cli("resolve", "https://contoso.visualstudio.com/Project/_boards")

    assert result.code != 0


def test_fetching_a_visualstudio_address_records_the_canonical_url(run_cli, ado_stub):
    work_item = {
        "id": 4242,
        "rev": 3,
        "fields": {
            "System.Title": "Export invoices",
            "System.State": "Active",
            "System.WorkItemType": "User Story",
            "System.TeamProject": "Big Project",
        },
        "relations": [],
    }
    ado_stub.route("/_apis/wit/workItems/4242", work_item)
    ado_stub.route("/comments", {"count": 0, "comments": []})

    result = run_cli(
        "fetch", "https://contoso.visualstudio.com/Big%20Project/_workitems/edit/4242"
    )

    assert result.code == 0, result.err
    assert result.json["ticket_json"]["url"] == CANONICAL
    assert all("visualstudio.com" not in url for _, url in ado_stub.requests)
