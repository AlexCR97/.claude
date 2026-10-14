import json

import pytest
from conftest import write_binding

pytestmark = pytest.mark.usefixtures("github_bound")

CANONICAL = "https://github.com/acme/web/issues/20"

FORMS = [
    "https://github.com/acme/web/issues/20",
    "http://github.com/acme/web/issues/20",
    "https://www.github.com/acme/web/issues/20",
    "https://github.com/acme/web/issues/20/",
    "https://github.com/acme/web/issues/20?notification_referrer_id=1",
    "https://github.com/acme/web/issues/20#issuecomment-99",
]


@pytest.mark.parametrize("address", FORMS)
def test_every_address_form_resolves_to_the_same_ticket(run_cli, address):
    result = run_cli("resolve", address)

    assert result.code == 0, result.err
    resolved = result.json
    assert resolved["source"] == "github"
    assert resolved["id"] == "20"
    assert resolved["coordinates"]["owner"] == "acme"
    assert resolved["coordinates"]["repository"] == "web"


@pytest.mark.parametrize("address", FORMS)
def test_a_pasted_address_is_reported_under_the_canonical_url(run_cli, address):
    assert run_cli("resolve", address).json["url"] == CANONICAL


def test_another_repository_resolves_to_its_own_coordinates(run_cli, tickets_home):
    write_binding(
        tickets_home,
        "github",
        "other",
        "tool",
        at_namespace={"owner": "other"},
        at_product={"repository": "tool"},
    )

    resolved = run_cli("resolve", "https://github.com/other/tool/issues/3").json

    assert resolved["coordinates"]["owner"] == "other"
    assert resolved["coordinates"]["repository"] == "tool"
    assert resolved["id"] == "3"


def test_a_pull_request_address_is_refused_as_not_a_ticket(run_cli):
    result = run_cli("resolve", "https://github.com/acme/web/pull/20")

    assert result.code != 0
    assert "pull request" in result.err.lower()


def test_an_address_with_no_issue_is_refused(run_cli):
    assert run_cli("resolve", "https://github.com/acme/web").code != 0


def test_fetching_an_address_records_the_canonical_url(run_cli, gh_stub):
    gh_stub.respond("issues/20/comments", "[]")
    gh_stub.respond(
        "repos/acme/web/issues/20",
        json.dumps(
            {
                "number": 20,
                "title": "Pull requests",
                "state": "open",
                "body": "Body.",
                "html_url": CANONICAL,
                "updated_at": "T1",
                "labels": [],
            }
        ),
    )

    result = run_cli("fetch", "https://github.com/acme/web/issues/20/")

    assert result.code == 0, result.err
    assert result.json["ticket_json"]["url"] == CANONICAL


def test_an_unbound_repository_is_reported_with_how_to_bind_it(run_cli):
    result = run_cli("resolve", "https://github.com/other/tool/issues/3")

    assert result.code != 0
    assert "ticket-setup" in result.err
