"""`fetch` mirrors an Azure DevOps work item into raw/ through a stub `az`: no network, no credentials."""

import json
from pathlib import Path

import pytest

TICKET = "acme/billing-app/ado/1234"
BOTH = ["--coordinate", "organization=acme", "--coordinate", "project=billing-app"]


@pytest.fixture
def bound(write_config):
    write_config("acme/namespace.json", {"sources": {"ado": {"organization": "acme"}}})
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"ado": {"project": "billing-app"}}},
    )


@pytest.fixture
def stub_work_item(az_stub):
    """Register a whole work item (no relations, no comments); a test changes any part."""

    def register(
        organization: str = "acme",
        project: str = "billing-app",
        number: int = 1234,
        **parts,
    ) -> str:
        base = f"https://dev.azure.com/{organization}"
        item = f"{base}/_apis/wit/workItems/{number}"
        fields = {
            "System.WorkItemType": "User Story",
            "System.TeamProject": project,
            "System.Title": "Cache the ledger lookup",
            "System.State": "Active",
            "System.Description": "<div>Lookups are slow.</div>",
            **parts.pop("fields", {}),
        }
        az_stub.respond(
            f"{item}?fields=System.TeamProject",
            {"id": number, "fields": {"System.TeamProject": project}},
        )
        work_item = {"id": number, "rev": parts.pop("rev", 7), "fields": fields}
        if "relations" in parts:
            work_item["relations"] = parts.pop("relations")
        az_stub.respond(f"{item}?$expand=all", work_item)
        related = parts.pop("related", {})
        if related:
            ids = ",".join(str(related_id) for related_id in sorted(related))
            az_stub.respond(
                f"{base}/_apis/wit/workitems?errorPolicy=Omit"
                f"&fields=System.Title,System.State,System.WorkItemType&ids={ids}",
                {
                    "count": len(related),
                    "value": [
                        {
                            "id": related_id,
                            "fields": {
                                "System.Title": title,
                                "System.State": state,
                                "System.WorkItemType": kind,
                            },
                        }
                        for related_id, (title, state, kind) in sorted(related.items())
                    ],
                },
            )
        encoded = project.replace(" ", "%20")
        az_stub.respond(
            f"{base}/{encoded}/_apis/wit/workItems/{number}/comments",
            {"comments": parts.pop("comments", [])},
        )
        return base

    return register


def read(sdlc_home: Path, relative: str) -> dict:
    return json.loads((sdlc_home / relative).read_text(encoding="utf-8"))


def test_a_fetch_mirrors_the_fields_and_comments_under_the_product_bound_to_the_project(
    run_cli, bound, stub_work_item, sdlc_home
):
    stub_work_item(
        comments=[{"id": 1, "text": "Which cache?"}, {"id": 2, "text": "Redis."}]
    )

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 0, result.err
    assert result.json["product"] == "acme/billing-app"
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    assert raw["meta"] == {
        "organization": "acme",
        "project": "billing-app",
        "work_item_id": 1234,
    }
    assert raw["work_item"]["fields"]["System.Title"] == "Cache the ledger lookup"
    assert [comment["text"] for comment in raw["comments"]] == [
        "Which cache?",
        "Redis.",
    ]


def test_a_fetch_records_what_the_source_determines_and_invents_no_type(
    run_cli, bound, stub_work_item, sdlc_home
):
    stub_work_item(rev=7)

    run_cli("fetch", "ado:1234", *BOTH)

    record = read(sdlc_home, f"{TICKET}/ticket.json")
    assert record["source"] == "ado"
    assert record["id"] == "1234"
    assert record["title"] == "Cache the ledger lookup"
    assert record["state"] == "Active"
    assert (
        record["url"] == "https://dev.azure.com/acme/billing-app/_workitems/edit/1234"
    )
    assert record["coordinates"] == {"organization": "acme", "project": "billing-app"}
    assert record["fingerprint"] == {"rev": 7}
    assert record["last_fetched_at"].endswith("+00:00")
    assert "type" not in record


def test_the_url_of_a_project_with_a_space_in_its_name_is_encoded(
    run_cli, write_config, stub_work_item, sdlc_home
):
    write_config("acme/namespace.json", {"sources": {"ado": {"organization": "acme"}}})
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"ado": {"project": "Billing App"}}},
    )
    stub_work_item(project="Billing App")

    result = run_cli(
        "fetch",
        "ado:1234",
        "--coordinate",
        "organization=acme",
        "--coordinate",
        "project=Billing App",
    )

    assert result.code == 0, result.err
    record = read(sdlc_home, f"{TICKET}/ticket.json")
    assert (
        record["url"] == "https://dev.azure.com/acme/Billing%20App/_workitems/edit/1234"
    )


@pytest.fixture
def two_projects(write_config):
    """One organization, two products, each bound to its own project."""
    write_config("acme/namespace.json", {"sources": {"ado": {"organization": "acme"}}})
    for product, project in (("billing-app", "billing-app"), ("ledger", "ledger")):
        write_config(
            f"acme/{product}/product.json", {"sources": {"ado": {"project": project}}}
        )


def test_the_first_intake_files_the_work_item_under_the_product_bound_to_its_team_project(
    run_cli, two_projects, stub_work_item, az_stub, sdlc_home
):
    stub_work_item(project="ledger")

    result = run_cli("fetch", "ado:1234")

    assert result.code == 0, result.err
    assert result.json["product"] == "acme/ledger"
    assert result.json["filing"]["rule"] == "address"
    assert (sdlc_home / "acme/ledger/ado/1234/raw/raw.json").is_file()
    assert not (sdlc_home / "acme/billing-app/ado/1234").exists()
    first = " ".join(az_stub.calls[0])
    assert "https://dev.azure.com/acme/_apis/wit/workItems/1234" in first
    assert "System.TeamProject" in first


def test_the_other_product_receives_a_work_item_of_its_own_project(
    run_cli, two_projects, stub_work_item, sdlc_home
):
    stub_work_item(project="billing-app")

    result = run_cli("fetch", "ado:1234")

    assert result.json["product"] == "acme/billing-app"


def test_without_a_binding_there_is_no_organization_to_read_from_and_setup_is_named(
    run_cli, stub_work_item, az_stub, sdlc_home
):
    stub_work_item()

    result = run_cli("fetch", "ado:1234")

    assert result.code == 1
    assert "no ado organization is bound" in result.err
    assert "/sdlc:setup" in result.err
    assert az_stub.calls == []
    assert not list(sdlc_home.glob("**/ado"))


def test_a_project_bound_nowhere_in_an_unbound_organization_is_an_error_naming_the_coordinates(
    run_cli, bound, stub_work_item, sdlc_home
):
    stub_work_item(organization="globex", project="payroll")

    result = run_cli("fetch", "ado:1234", "--coordinate", "organization=globex")

    assert result.code == 1
    assert "organization 'globex'" in result.err
    assert "project 'payroll'" in result.err
    assert "/sdlc:setup" in result.err
    assert not list(sdlc_home.glob("**/ado"))


def test_a_project_unbound_in_a_bound_organization_lands_in_that_namespace_default_product(
    run_cli, bound, stub_work_item, sdlc_home
):
    stub_work_item(project="payroll")

    result = run_cli("fetch", "ado:1234")

    assert result.code == 0, result.err
    assert result.json["product"] == "acme/default"
    assert read(sdlc_home, "acme/default/ado/1234/ticket.json")["coordinates"] == {
        "organization": "acme",
        "project": "payroll",
    }


def test_two_bound_organizations_need_the_context_or_a_coordinate_to_pick_one(
    run_cli, bound, stub_work_item, write_config, az_stub, sdlc_home
):
    write_config(
        "globex/namespace.json", {"sources": {"ado": {"organization": "globex"}}}
    )
    write_config(
        "globex/payroll/product.json", {"sources": {"ado": {"project": "payroll"}}}
    )
    stub_work_item(organization="globex", project="payroll")

    ambiguous = run_cli("fetch", "ado:1234")
    by_context = run_cli("fetch", "ado:1234", "--context", "globex")

    assert ambiguous.code == 3
    assert "acme" in ambiguous.err and "globex" in ambiguous.err
    assert by_context.code == 0, by_context.err
    assert by_context.json["product"] == "globex/payroll"


def test_a_refresh_keeps_the_recorded_type_and_other_keys_and_takes_the_new_revision(
    run_cli, two_projects, stub_work_item, az_stub, sdlc_home
):
    stub_work_item(project="ledger", rev=7)
    run_cli("fetch", "ado:1234")
    path = sdlc_home / "acme/ledger/ado/1234/ticket.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps({**record, "type": "bug", "origin": "notes.md"}), encoding="utf-8"
    )
    stub_work_item(project="ledger", rev=8, fields={"System.State": "Closed"})

    result = run_cli("fetch", "ado:1234")

    assert result.code == 0, result.err
    refreshed = json.loads(path.read_text(encoding="utf-8"))
    assert refreshed["type"] == "bug"
    assert refreshed["origin"] == "notes.md"
    assert refreshed["state"] == "Closed"
    assert refreshed["fingerprint"] == {"rev": 8}


def test_a_refresh_reads_the_ticket_by_its_own_coordinates_without_asking_for_the_project_again(
    run_cli, two_projects, stub_work_item, az_stub
):
    stub_work_item(project="ledger")
    run_cli("fetch", "ado:1234")
    before = len(az_stub.calls)

    run_cli("fetch", "ado:1234")

    new_calls = [" ".join(call) for call in az_stub.calls[before:]]
    assert not any("System.TeamProject" in call for call in new_calls)


def link(rel: str, number: int, **attributes) -> dict:
    return {
        "rel": rel,
        "url": f"https://dev.azure.com/acme/_apis/wit/workItems/{number}",
        "attributes": attributes,
    }


def test_the_mirror_holds_every_relation_with_the_id_title_state_and_type_of_each_related_work_item(
    run_cli, bound, stub_work_item, sdlc_home
):
    stub_work_item(
        relations=[
            link("System.LinkTypes.Hierarchy-Reverse", 1000),
            link("System.LinkTypes.Hierarchy-Forward", 1235),
            link("System.LinkTypes.Dependency-Reverse", 1100),
            link("System.LinkTypes.Dependency-Forward", 1300),
            link("System.LinkTypes.Related", 1400),
            {
                "rel": "Hyperlink",
                "url": "https://wiki.example.test/ledger",
                "attributes": {"comment": "Design notes"},
            },
            {
                "rel": "ArtifactLink",
                "url": "vstfs:///Git/PullRequestId/abc%2Fdef%2F12",
                "attributes": {"name": "Pull Request"},
            },
        ],
        related={
            1000: ("Billing revamp", "Active", "Epic"),
            1100: ("Pick a cache", "Closed", "Task"),
            1235: ("Evict stale keys", "New", "Task"),
            1300: ("Dashboard", "New", "User Story"),
            1400: ("Audit export", "Active", "Bug"),
        },
    )

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 0, result.err
    relations = read(sdlc_home, f"{TICKET}/raw/raw.json")["relations"]
    assert relations["parent"] == {
        "id": 1000,
        "title": "Billing revamp",
        "state": "Active",
        "type": "Epic",
    }
    assert [item["id"] for item in relations["children"]] == [1235]
    assert relations["predecessors"] == [
        {"id": 1100, "title": "Pick a cache", "state": "Closed", "type": "Task"}
    ]
    assert [(item["id"], item["state"]) for item in relations["successors"]] == [
        (1300, "New")
    ]
    assert [(item["id"], item["type"]) for item in relations["related"]] == [
        (1400, "Bug")
    ]
    assert relations["hyperlinks"] == [
        {"url": "https://wiki.example.test/ledger", "comment": "Design notes"}
    ]
    assert relations["other"][0]["rel"] == "ArtifactLink"
    assert result.json["fetched"]["relations"] == {
        "parent": True,
        "children": 1,
        "predecessors": 1,
        "successors": 1,
        "related": 1,
        "hyperlinks": 1,
        "other": 1,
    }


def test_a_work_item_without_relations_has_no_parent_and_empty_lists(
    run_cli, bound, stub_work_item, sdlc_home
):
    stub_work_item()

    run_cli("fetch", "ado:1234", *BOTH)

    relations = read(sdlc_home, f"{TICKET}/raw/raw.json")["relations"]
    assert relations["parent"] is None
    assert relations["children"] == relations["related"] == []


def test_comments_are_read_page_by_page_until_none_is_left(
    run_cli, bound, stub_work_item, az_stub, sdlc_home
):
    base = stub_work_item(comments=[{"id": 1, "text": "first"}])
    comments = f"{base}/billing-app/_apis/wit/workItems/1234/comments"
    az_stub.respond(
        comments, {"comments": [{"id": 1, "text": "first"}], "continuationToken": "abc"}
    )
    az_stub.respond(
        f"{comments}?continuationToken=abc", {"comments": [{"id": 2, "text": "second"}]}
    )

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 0, result.err
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    assert [comment["text"] for comment in raw["comments"]] == ["first", "second"]


GUID_FILE = "11111111-aaaa-4aaa-8aaa-111111111111"
GUID_PASTED = "22222222-bbbb-4bbb-8bbb-222222222222"
GUID_COMMENT = "33333333-cccc-4ccc-8ccc-333333333333"
ATTACHMENTS = "https://dev.azure.com/acme/0f1e2d3c-project/_apis/wit/attachments"


@pytest.fixture
def with_attachments(stub_work_item, az_stub):
    """A work item holding an attached file, an image pasted into the description and one in a comment."""
    az_stub.respond_bytes(f"{ATTACHMENTS}/{GUID_FILE}", b"PK\x03\x04archive")
    az_stub.respond_bytes(f"{ATTACHMENTS}/{GUID_PASTED}", b"\x89PNGpasted")
    az_stub.respond_bytes(f"{ATTACHMENTS}/{GUID_COMMENT}", b"\x89PNGcomment")
    stub_work_item(
        fields={
            "System.Description": f'<img src="{ATTACHMENTS}/{GUID_PASTED}?fileName=image.png">'
        },
        relations=[
            {
                "rel": "AttachedFile",
                "url": f"{ATTACHMENTS}/{GUID_FILE}",
                "attributes": {"name": "ledger-export.zip"},
            }
        ],
        comments=[
            {
                "id": 9,
                "text": f'<div><img src="{ATTACHMENTS}/{GUID_COMMENT}?fileName=image.png"></div>',
            }
        ],
    )


def test_every_attachment_reference_is_recorded_and_downloaded_under_its_guid(
    run_cli, bound, with_attachments, sdlc_home
):
    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 0, result.err
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    recorded = {
        item["url"].rsplit("/", 1)[-1].split("?")[0]: item
        for item in raw["attachments"]
    }
    assert set(recorded) == {GUID_FILE, GUID_PASTED, GUID_COMMENT}
    assert recorded[GUID_FILE]["name"] == "ledger-export.zip"
    assert recorded[GUID_FILE]["local_filename"] == f"{GUID_FILE}.zip"
    assert recorded[GUID_PASTED]["name"] == "image.png"
    assert recorded[GUID_PASTED]["found_in"] == "field:System.Description"
    assert recorded[GUID_COMMENT]["found_in"] == "comment:9"
    raw_dir = sdlc_home / TICKET / "raw"
    assert (raw_dir / f"{GUID_FILE}.zip").read_bytes() == b"PK\x03\x04archive"
    assert (raw_dir / f"{GUID_PASTED}.png").read_bytes() == b"\x89PNGpasted"
    assert result.json["fetched"]["attachments"] == {
        "found": 3,
        "downloaded": 3,
        "kept": 0,
        "failed": [],
    }


def test_an_attachment_that_cannot_be_downloaded_is_recorded_and_reported_not_fatal(
    run_cli, bound, with_attachments, az_stub, sdlc_home
):
    az_stub.fail(f"{ATTACHMENTS}/{GUID_PASTED}", "Forbidden")

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 0, result.err
    report = result.json["fetched"]["attachments"]
    assert report["downloaded"] == 2
    assert [item["url"].rsplit("?")[0] for item in report["failed"]] == [
        f"{ATTACHMENTS}/{GUID_PASTED}"
    ]
    assert "Forbidden" in report["failed"][0]["error"]
    raw = read(sdlc_home, f"{TICKET}/raw/raw.json")
    pasted = next(a for a in raw["attachments"] if GUID_PASTED in a["url"])
    assert pasted["local_filename"] is None
    assert not (sdlc_home / TICKET / "raw" / f"{GUID_PASTED}.png").exists()


def test_a_refresh_keeps_the_files_it_already_downloaded_and_fetches_only_new_ones(
    run_cli, bound, with_attachments, az_stub, sdlc_home
):
    run_cli("fetch", "ado:1234", *BOTH)
    kept = sdlc_home / TICKET / "raw" / f"{GUID_FILE}.zip"
    kept.write_bytes(b"edited by hand")
    downloads_before = sum(GUID_FILE in " ".join(call) for call in az_stub.calls)

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 0, result.err
    assert kept.read_bytes() == b"edited by hand"
    assert (
        sum(GUID_FILE in " ".join(call) for call in az_stub.calls) == downloads_before
    )
    assert result.json["fetched"]["attachments"]["kept"] == 3
    assert result.json["fetched"]["attachments"]["downloaded"] == 0


def test_only_az_rest_is_ever_run_and_no_credential_is_passed_to_it(
    run_cli, bound, with_attachments, az_stub
):
    run_cli("fetch", "ado:1234", *BOTH)

    assert az_stub.calls
    for call in az_stub.calls:
        assert call[0] == "rest"
        assert "--headers" not in call
        assert "--access-token" not in call


def test_a_rejected_sign_in_aborts_with_nothing_written_and_says_how_to_sign_in(
    run_cli, bound, stub_work_item, az_stub, sdlc_home
):
    base = stub_work_item()
    az_stub.fail(
        f"{base}/_apis/wit/workItems/1234?$expand=all",
        "AADSTS700082: The refresh token has expired. Run az login.",
    )

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 1
    assert (
        "az login --scope 499b84ac-1321-427f-aa17-267ca6975798/.default" in result.err
    )
    assert not list(sdlc_home.glob("**/ado"))


def test_a_work_item_that_does_not_exist_exits_not_found_with_nothing_written(
    run_cli, bound, stub_work_item, az_stub, sdlc_home
):
    base = stub_work_item()
    az_stub.fail(
        f"{base}/_apis/wit/workItems/1234?fields=System.TeamProject",
        'Not Found({"message":"TF401232: Work item 1234 does not exist, or you do not have permissions to read it."})',
    )

    result = run_cli("fetch", "ado:1234")

    assert result.code == 5
    assert "1234" in result.err
    assert not list(sdlc_home.glob("**/ado"))


@pytest.mark.parametrize("failing", ["comments", "related"])
def test_a_failed_request_for_a_part_of_the_mirror_aborts_instead_of_writing_a_partial_one(
    run_cli, bound, stub_work_item, az_stub, sdlc_home, failing
):
    base = stub_work_item(
        relations=[link("System.LinkTypes.Related", 1400)],
        related={1400: ("Audit export", "Active", "Bug")},
    )
    route = {
        "comments": f"{base}/billing-app/_apis/wit/workItems/1234/comments",
        "related": f"{base}/_apis/wit/workitems?errorPolicy=Omit"
        "&fields=System.Title,System.State,System.WorkItemType&ids=1400",
    }[failing]
    az_stub.fail(route, "Service Unavailable")

    result = run_cli("fetch", "ado:1234", *BOTH)

    assert result.code == 1
    assert not list(sdlc_home.glob("**/ado"))
