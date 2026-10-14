import json
import re
from pathlib import Path

import pytest

GITHUB_PR = "https://github.com/acme/web/pull/123"


@pytest.fixture
def ticket(local_ticket):
    return local_ticket()


def record(ticket) -> Path:
    return Path(ticket["paths"]["ticket_dir"]) / "pulls.md"


def add(run_cli, ticket, url):
    return run_cli("pulls", "add", ticket["ref"], url)


def test_a_pull_request_is_recorded_as_a_link(run_cli, ticket):
    result = add(run_cli, ticket, GITHUB_PR)

    assert result.code == 0, result.err
    assert f"[acme/web#123]({GITHUB_PR})" in record(ticket).read_text(encoding="utf-8")


def test_a_second_pull_request_is_added_beside_the_first(run_cli, ticket):
    other = "https://github.com/acme/web/pull/124"
    add(run_cli, ticket, GITHUB_PR)

    add(run_cli, ticket, other)

    text = record(ticket).read_text(encoding="utf-8")
    assert GITHUB_PR in text and other in text


def test_the_same_pull_request_is_recorded_once(run_cli, ticket):
    add(run_cli, ticket, GITHUB_PR)

    again = add(run_cli, ticket, GITHUB_PR)

    assert again.code == 0
    assert record(ticket).read_text(encoding="utf-8").count(f"]({GITHUB_PR})") == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://dev.azure.com/contoso/Big%20Project/_git/api/pullrequest/42",
        "https://contoso.visualstudio.com/Big%20Project/_git/api/pullrequest/42",
    ],
)
def test_an_azure_devops_pull_request_is_recorded_under_either_address_form(
    run_cli, ticket, url
):
    result = add(run_cli, ticket, url)

    assert result.code == 0, result.err
    assert f"[Big Project/api!42]({url})" in record(ticket).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/acme/web/-/merge_requests/5",
        "https://github.com/acme/web/issues/7",
        "not a url",
    ],
)
def test_an_address_that_is_not_a_pull_request_is_refused_and_nothing_is_written(
    run_cli, ticket, url
):
    result = add(run_cli, ticket, url)

    assert result.code == 1
    assert url in result.err
    assert not record(ticket).exists()


def test_a_pull_request_that_delivers_two_tickets_is_listed_in_both(
    run_cli, local_ticket
):
    first, second = local_ticket("First"), local_ticket("Second")

    add(run_cli, first, GITHUB_PR)
    add(run_cli, second, GITHUB_PR)

    assert GITHUB_PR in record(first).read_text(encoding="utf-8")
    assert GITHUB_PR in record(second).read_text(encoding="utf-8")


def github_state(state="OPEN", draft=False, review="", checks=()):
    return json.dumps(
        {
            "state": state,
            "isDraft": draft,
            "reviewDecision": review,
            "statusCheckRollup": [
                {"conclusion": c, "status": "COMPLETED"} for c in checks
            ],
        }
    )


def refresh(run_cli, ticket):
    return run_cli("pulls", "refresh", ticket["ref"])


def test_a_refresh_writes_each_pull_requests_status_and_the_time(
    run_cli, ticket, gh_stub
):
    add(run_cli, ticket, GITHUB_PR)
    gh_stub.respond("pr view", github_state(review="APPROVED"))

    result = refresh(run_cli, ticket)

    assert result.code == 0, result.err
    text = record(ticket).read_text(encoding="utf-8")
    assert f"- [acme/web#123]({GITHUB_PR}) — open, approved" in text
    assert re.search(r"Status as of \d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC", text)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (github_state(draft=True), "draft"),
        (github_state(state="MERGED"), "merged"),
        (github_state(state="CLOSED"), "closed"),
        (github_state(review="CHANGES_REQUESTED"), "open, changes requested"),
        (github_state(checks=["SUCCESS", "SUCCESS"]), "open, checks passing"),
        (github_state(checks=["SUCCESS", "FAILURE"]), "open, checks failing"),
        (
            json.dumps(
                {
                    "state": "OPEN",
                    "isDraft": False,
                    "reviewDecision": "",
                    "statusCheckRollup": [{"status": "IN_PROGRESS", "conclusion": ""}],
                }
            ),
            "open, checks pending",
        ),
    ],
)
def test_the_status_reads_state_checks_and_review(
    run_cli, ticket, gh_stub, response, expected
):
    add(run_cli, ticket, GITHUB_PR)
    gh_stub.respond("pr view", response)

    refresh(run_cli, ticket)

    assert f"({GITHUB_PR}) — {expected}\n" in record(ticket).read_text(encoding="utf-8")


def test_a_failed_refresh_keeps_the_old_statuses_and_says_it_failed(
    run_cli, ticket, gh_stub
):
    add(run_cli, ticket, GITHUB_PR)
    gh_stub.respond("pr view", github_state(review="APPROVED"))
    refresh(run_cli, ticket)
    before = record(ticket).read_text(encoding="utf-8")
    stamp = re.search(r"Status as of (.+)\.", before).group(1)
    gh_stub.respond("pr view", "", code=1)

    result = refresh(run_cli, ticket)

    assert result.code == 1
    after = record(ticket).read_text(encoding="utf-8")
    assert f"({GITHUB_PR}) — open, approved\n" in after
    assert f"Status as of {stamp}." in after
    assert "Refresh failed" in after
    assert "Refresh failed" in result.err


ADO_PR = "https://dev.azure.com/contoso/Big%20Project/_git/api/pullrequest/42"


@pytest.mark.parametrize(
    ("pull_request", "expected"),
    [
        (
            {"status": "active", "isDraft": False, "reviewers": [{"vote": 10}]},
            "open, approved",
        ),
        ({"status": "active", "isDraft": True, "reviewers": []}, "draft"),
        (
            {
                "status": "active",
                "isDraft": False,
                "reviewers": [{"vote": 10}, {"vote": -5}],
            },
            "open, waiting for author",
        ),
        (
            {"status": "active", "isDraft": False, "reviewers": [{"vote": -10}]},
            "open, rejected",
        ),
        ({"status": "completed", "isDraft": False, "reviewers": []}, "merged"),
        ({"status": "abandoned", "isDraft": False, "reviewers": []}, "closed"),
    ],
)
def test_an_azure_devops_status_reads_state_and_votes(
    run_cli, ticket, ado_stub, pull_request, expected
):
    add(run_cli, ticket, ADO_PR)
    ado_stub.route("repositories/api/pullrequests/42", pull_request)

    result = refresh(run_cli, ticket)

    assert result.code == 0, result.err
    assert f"({ADO_PR}) — {expected}\n" in record(ticket).read_text(encoding="utf-8")
    assert any(
        "dev.azure.com/contoso/Big%20Project/_apis/git" in url
        for _, url in ado_stub.requests
    )


PLAN = """# Implementation Plan

## Workspace

### Worktrees

| Repository | Branch | Kind | Path |
| ---------- | ------ | ---- | ---- |
{rows}

### Projects

| Project | Lives in | Path | Technology |
| ------- | -------- | ---- | ---------- |
| api | repo | src/Api | .NET |
"""


def write_plan(ticket, *worktrees):
    rows = "\n".join(
        f"| {w.path.name} | {w.git('branch', '--show-current')} | linked | `{w.path}` |"
        for w in worktrees
    )
    plan = Path(ticket["paths"]["ticket_dir"]) / "plan.md"
    plan.write_text(PLAN.format(rows=rows), encoding="utf-8")


def discover(run_cli, ticket):
    return run_cli("pulls", "discover", ticket["ref"])


def test_a_pull_request_on_a_planned_branch_is_discovered(
    run_cli, ticket, gh_stub, repository
):
    repository.git("checkout", "-b", "feat/1-invoice")
    write_plan(ticket, repository)
    gh_stub.respond("pr list", json.dumps([{"url": GITHUB_PR}]))

    result = discover(run_cli, ticket)

    assert result.code == 0, result.err
    assert f"[acme/web#123]({GITHUB_PR})" in record(ticket).read_text(encoding="utf-8")
    assert any("--head" in call and "feat/1-invoice" in call for call in gh_stub.calls)


def test_discovery_skips_a_protected_branch_and_a_branch_the_plan_does_not_list(
    run_cli, ticket, gh_stub, make_repository
):
    planned, on_main, unlisted = (
        make_repository("a"),
        make_repository("b"),
        make_repository("c"),
    )
    planned.git("checkout", "-b", "feat/1-invoice")
    unlisted.git("checkout", "-b", "feat/9-other")
    write_plan(ticket, planned, on_main)
    gh_stub.respond("pr list", json.dumps([]))

    discover(run_cli, ticket)

    heads = [
        call[call.index("--head") + 1] for call in gh_stub.calls if "--head" in call
    ]
    assert heads == ["feat/1-invoice"]


def test_a_refresh_never_edits_or_reorders_the_links(
    run_cli, ticket, gh_stub, ado_stub
):
    urls = [GITHUB_PR, ADO_PR, "https://github.com/acme/web/pull/124"]
    for url in urls:
        add(run_cli, ticket, url)
    gh_stub.respond("pr view", github_state(state="MERGED"))
    ado_stub.route(
        "pullrequests/42", {"status": "active", "isDraft": False, "reviewers": []}
    )

    result = refresh(run_cli, ticket)

    assert result.code == 0, result.err
    links = re.findall(r"\]\((\S+?)\)", record(ticket).read_text(encoding="utf-8"))
    assert links == urls


def test_a_refresh_with_no_pull_requests_creates_nothing(run_cli, ticket):
    result = refresh(run_cli, ticket)

    assert result.code == 0
    assert not record(ticket).exists()


def test_output_gh_cannot_be_read_fails_the_refresh_instead_of_crashing(
    run_cli, ticket, gh_stub
):
    add(run_cli, ticket, GITHUB_PR)
    gh_stub.respond("pr view", "this is not json")

    result = refresh(run_cli, ticket)

    assert result.code == 1
    assert "Traceback" not in result.err
    assert "Refresh failed" in record(ticket).read_text(encoding="utf-8")


def test_an_azure_devops_status_the_table_does_not_know_is_shown_as_it_is(
    run_cli, ticket, ado_stub
):
    add(run_cli, ticket, ADO_PR)
    ado_stub.route(
        "pullrequests/42", {"status": "notSet", "isDraft": False, "reviewers": []}
    )

    result = refresh(run_cli, ticket)

    assert result.code == 0, result.err
    assert f"({ADO_PR}) — notSet\n" in record(ticket).read_text(encoding="utf-8")
