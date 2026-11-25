"""`sync` keeps a ticket's mirror and its pull request record current, in one call a skill makes at its start."""

import re
from pathlib import Path

import pytest

GITHUB = "acme/billing-app/github/1234"


@pytest.fixture
def bound(write_config):
    write_config(
        "acme/namespace.json",
        {"sources": {"github": {"owner": "acme"}, "ado": {"organization": "acme"}}},
    )
    write_config(
        "acme/billing-app/product.json",
        {
            "sources": {
                "github": {"repository": "billing-app"},
                "ado": {"project": "billing-app"},
            }
        },
    )


def raw_of(sdlc_home: Path, ticket: str) -> bytes:
    return (sdlc_home / ticket / "raw" / "raw.json").read_bytes()


def test_an_unchanged_ticket_is_not_refreshed_and_names_no_field(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue()
    run_cli("fetch", "github:1234")
    mirror = raw_of(sdlc_home, GITHUB)

    result = run_cli("sync", "github:1234")

    assert result.code == 0, result.err
    report = result.json
    assert report["upstream"] == {
        "status": "unchanged",
        "refreshed": False,
        "fields": [],
        "journal": [],
    }
    assert report["changed"] is False
    assert raw_of(sdlc_home, GITHUB) == mirror


ENTRY = "# Journal entry - [#1234: Cache the ledger lookup](https://example.test)\n\n**Next:** write the cache test\n"


def posted(name: str) -> dict:
    return {
        "id": 77,
        "body": f"sdlc-journal-entry `{name}`\n\n{ENTRY}",
        "user": {"login": "pablo"},
    }


def test_a_ticket_whose_only_change_is_this_machines_journal_post_is_not_refreshed(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue()
    run_cli("fetch", "github:1234")
    mirror = raw_of(sdlc_home, GITHUB)
    name = "2026-11-25T10-00-00Z.md"
    (sdlc_home / GITHUB / "journal").mkdir()
    (sdlc_home / GITHUB / "journal" / name).write_text(ENTRY, encoding="utf-8")
    stub_issue(comments=[posted(name)])

    result = run_cli("sync", "github:1234")

    assert result.code == 0, result.err
    assert result.json["upstream"]["status"] == "journal_only"
    assert result.json["upstream"]["refreshed"] is False
    assert result.json["changed"] is False
    assert raw_of(sdlc_home, GITHUB) == mirror


def test_a_journal_entry_posted_from_elsewhere_refreshes_the_mirror_and_is_named(
    run_cli, bound, stub_issue, sdlc_home
):
    stub_issue()
    run_cli("fetch", "github:1234")
    name = "2026-11-25T10-00-00Z.md"
    stub_issue(comments=[posted(name)])

    result = run_cli("sync", "github:1234")

    assert result.code == 0, result.err
    upstream = result.json["upstream"]
    assert upstream["status"] == "journal_unmirrored"
    assert upstream["refreshed"] is True
    assert upstream["fields"] == []
    assert upstream["journal"] == [name]
    assert result.json["changed"] is True
    assert (sdlc_home / GITHUB / "journal" / name).read_text(encoding="utf-8") == ENTRY


BODY = "Lookups are slow.\n\n## Acceptance Criteria\n\n- [ ] p95 under 50 ms\n\n## Notes\n\nSee the dashboard."


@pytest.mark.parametrize(
    ("edit", "fields"),
    [
        (
            {"body": BODY.replace("Lookups are slow.", "Lookups time out.")},
            ["description"],
        ),
        ({"body": BODY.replace("50 ms", "20 ms")}, ["acceptance_criteria"]),
        ({"body": BODY.replace("the dashboard", "Grafana")}, ["description"]),
        (
            {"title": "Cache every ledger lookup", "labels": [{"name": "bug"}]},
            ["title", "labels"],
        ),
    ],
)
def test_a_ticket_changed_upstream_is_refreshed_and_names_the_fields_that_changed(
    run_cli, bound, stub_issue, sdlc_home, edit, fields
):
    stub_issue(issue={"body": BODY})
    run_cli("fetch", "github:1234")
    stub_issue(issue={"body": BODY, **edit})

    result = run_cli("sync", "github:1234")

    assert result.code == 0, result.err
    upstream = result.json["upstream"]
    assert upstream["status"] == "changed"
    assert upstream["refreshed"] is True
    assert upstream["fields"] == fields
    assert result.json["changed"] is True
    record = (sdlc_home / GITHUB / "ticket.json").read_text(encoding="utf-8")
    assert edit.get("title", "Cache the ledger lookup") in record


def test_a_new_comment_upstream_is_named_as_a_changed_field(run_cli, bound, stub_issue):
    stub_issue()
    run_cli("fetch", "github:1234")
    stub_issue(comments=[{"id": 9, "body": "Use Redis.", "user": {"login": "ana"}}])

    result = run_cli("sync", "github:1234")

    assert result.json["upstream"]["fields"] == ["comments"]


ADO = "acme/billing-app/ado/1234"
CRITERIA = "Microsoft.VSTS.Common.AcceptanceCriteria"


def probe(az_stub, rev: int) -> None:
    az_stub.respond(
        "https://dev.azure.com/acme/_apis/wit/workItems/1234?fields=System.Rev",
        {"id": 1234, "rev": rev, "fields": {"System.Rev": rev}},
    )


@pytest.mark.parametrize(
    ("edit", "fields"),
    [
        ({CRITERIA: "<ul><li>p95 under 20 ms</li></ul>"}, ["acceptance_criteria"]),
        ({"System.Description": "<div>Lookups time out.</div>"}, ["description"]),
        ({"System.Tags": "cache; perf"}, ["tags"]),
        ({"System.AssignedTo": "Ana"}, ["System.AssignedTo"]),
    ],
)
def test_a_work_item_changed_upstream_names_its_fields_in_the_tickets_terms(
    run_cli, bound, stub_work_item, az_stub, edit, fields
):
    original = {CRITERIA: "<ul><li>p95 under 50 ms</li></ul>"}
    stub_work_item(fields=original)
    assert run_cli("fetch", "ado:1234").code == 0
    stub_work_item(fields={**original, **edit}, rev=9)
    probe(az_stub, 9)

    result = run_cli("sync", "ado:1234")

    assert result.code == 0, result.err
    assert result.json["upstream"]["status"] == "changed"
    assert result.json["upstream"]["fields"] == fields


BRANCH = "feat/1234-cache-ledger"
PULL = "https://github.com/acme/billing-app/pull/12"


def write_plan(ticket_dir: Path, *worktrees: tuple[str, str, Path]) -> None:
    rows = "\n".join(
        f"| {repository} | {branch} | linked | `{path}` |"
        for repository, branch, path in worktrees
    )
    (ticket_dir / "plan.md").write_text(
        "# Implementation Plan - [github:1234: Cache](https://example.test)\n\n"
        "## Workspace\n\n### Worktrees\n\n"
        "| Repository | Branch | Kind | Path |\n| --- | --- | --- | --- |\n"
        f"{rows}\n\n## Phase 1: Build\n",
        encoding="utf-8",
    )


def pull(number: int = 12, **parts) -> dict:
    return {
        "number": number,
        "url": f"https://github.com/acme/billing-app/pull/{number}",
        "state": "OPEN",
        "isDraft": False,
        "reviewDecision": "",
        "statusCheckRollup": [],
        **parts,
    }


@pytest.fixture
def github_ticket(run_cli, bound, stub_issue, sdlc_home) -> Path:
    stub_issue()
    assert run_cli("fetch", "github:1234").code == 0
    return sdlc_home / GITHUB


@pytest.fixture
def on_github(repository):
    repository.git("checkout", "-b", BRANCH)
    repository.git(
        "remote", "set-url", "origin", "https://github.com/acme/billing-app.git"
    )
    return repository


def test_pull_requests_headed_by_a_workspace_branch_are_recorded_with_their_status(
    run_cli, github_ticket, on_github, gh_stub
):
    write_plan(github_ticket, ("billing-app", BRANCH, on_github.path))
    gh_stub.respond(
        f"pr list acme/billing-app {BRANCH}",
        [
            pull(
                reviewDecision="APPROVED",
                statusCheckRollup=[{"status": "COMPLETED", "conclusion": "SUCCESS"}],
            )
        ],
    )

    result = run_cli("sync", "github:1234")

    assert result.code == 0, result.err
    assert result.json["pulls"]["lines"] == [
        {
            "label": "acme/billing-app#12",
            "url": PULL,
            "status": "open, checks passing, approved",
        }
    ]
    assert result.json["changed"] is True
    record = (github_ticket / "pulls.md").read_text(encoding="utf-8")
    assert re.fullmatch(
        r"# Pull requests\n\nStatus as of \d{4}-\d\d-\d\d \d\d:\d\d UTC\.\n\n"
        rf"- \[acme/billing-app#12\]\({re.escape(PULL)}\) - open, checks passing, approved\n",
        record,
    ), record


@pytest.mark.parametrize(
    ("parts", "status"),
    [
        ({"isDraft": True}, "draft"),
        (
            {"statusCheckRollup": [{"status": "COMPLETED", "conclusion": "FAILURE"}]},
            "open, checks failing",
        ),
        (
            {
                "statusCheckRollup": [
                    {"status": "IN_PROGRESS", "conclusion": ""},
                    {"state": "SUCCESS"},
                ],
                "reviewDecision": "CHANGES_REQUESTED",
            },
            "open, checks pending, changes requested",
        ),
        (
            {
                "state": "MERGED",
                "reviewDecision": "APPROVED",
                "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
            },
            "merged",
        ),
        ({"state": "CLOSED"}, "closed"),
    ],
)
def test_a_pull_requests_status_is_the_hosts_own(
    run_cli, github_ticket, on_github, gh_stub, parts, status
):
    write_plan(github_ticket, ("billing-app", BRANCH, on_github.path))
    gh_stub.respond(f"pr list acme/billing-app {BRANCH}", [pull(**parts)])

    result = run_cli("sync", "github:1234")

    assert result.json["pulls"]["lines"][0]["status"] == status


def test_a_protected_branch_in_the_workspace_is_not_asked_about(
    run_cli, github_ticket, repository, gh_stub
):
    repository.git(
        "remote", "set-url", "origin", "https://github.com/acme/billing-app.git"
    )
    write_plan(github_ticket, ("billing-app", "main", repository.path))

    result = run_cli("sync", "github:1234")

    assert result.code == 0, result.err
    assert result.json["pulls"]["lines"] == []
    assert result.json["pulls"]["skipped"][0]["branch"] == "main"
    assert not any(call[:2] == ["pr", "list"] for call in gh_stub.calls)
    record = (github_ticket / "pulls.md").read_text(encoding="utf-8")
    assert "No pull requests deliver this ticket yet." in record


def test_a_recorded_pull_request_and_one_named_are_refreshed_beside_those_found(
    run_cli, github_ticket, on_github, gh_stub
):
    write_plan(github_ticket, ("billing-app", BRANCH, on_github.path))
    recorded = "https://github.com/acme/ledger/pull/3"
    named = "https://github.com/acme/ledger/pull/4"
    (github_ticket / "pulls.md").write_text(
        "# Pull requests\n\nStatus as of 2026-11-20 09:00 UTC.\n\n"
        f"- [acme/ledger#3]({recorded}) - draft\n",
        encoding="utf-8",
    )
    gh_stub.respond(f"pr list acme/billing-app {BRANCH}", [pull()])
    gh_stub.respond(f"pr view {recorded}", pull(3, url=recorded, state="MERGED"))
    gh_stub.respond(f"pr view {named}", pull(4, url=named))

    result = run_cli("sync", "github:1234", "--pull", named)

    assert result.code == 0, result.err
    assert result.json["pulls"]["lines"] == [
        {"label": "acme/ledger#3", "url": recorded, "status": "merged"},
        {"label": "acme/ledger#4", "url": named, "status": "open"},
        {"label": "acme/billing-app#12", "url": PULL, "status": "open"},
    ]
    assert result.json["pulls"]["changed"] is True


def test_an_unchanged_record_is_not_reported_as_a_change(
    run_cli, github_ticket, on_github, gh_stub
):
    write_plan(github_ticket, ("billing-app", BRANCH, on_github.path))
    gh_stub.respond(f"pr list acme/billing-app {BRANCH}", [pull()])
    assert run_cli("sync", "github:1234").json["changed"] is True

    result = run_cli("sync", "github:1234")

    assert result.json["pulls"]["changed"] is False
    assert result.json["changed"] is False


RECORD = (
    "# Pull requests\n\nStatus as of 2026-11-20 09:00 UTC.\n\n"
    f"- [acme/billing-app#12]({PULL}) - draft\n"
)


def test_a_failure_exits_with_its_error_and_leaves_the_mirror_and_the_record_as_they_were(
    run_cli, github_ticket, on_github, gh_stub, stub_issue, sdlc_home
):
    write_plan(github_ticket, ("billing-app", BRANCH, on_github.path))
    (github_ticket / "pulls.md").write_text(RECORD, encoding="utf-8")
    mirror = raw_of(sdlc_home, GITHUB)
    stub_issue(issue={"title": "Cache every ledger lookup"})
    gh_stub.fail(
        f"pr list acme/billing-app {BRANCH}", "error connecting to api.github.com"
    )

    result = run_cli("sync", "github:1234")

    assert result.code == 1
    assert "error connecting to api.github.com" in result.err
    assert raw_of(sdlc_home, GITHUB) == mirror
    record = (github_ticket / "pulls.md").read_text(encoding="utf-8")
    assert record.startswith(RECORD)
    assert re.search(
        r"^Refresh failed: .*error connecting to api\.github\.com.*\.$",
        record,
        re.MULTILINE,
    )


def test_a_signed_out_check_marks_the_record_failed_and_a_later_sync_clears_it(
    run_cli, github_ticket, gh_stub, stub_issue
):
    (github_ticket / "pulls.md").write_text(RECORD, encoding="utf-8")
    gh_stub.fail("auth status", "You are not logged into any GitHub hosts.")

    failed = run_cli("sync", "github:1234")

    assert failed.code == 1
    assert "not signed in" in failed.err
    record = (github_ticket / "pulls.md").read_text(encoding="utf-8")
    assert record.count("Refresh failed:") == 1
    assert "draft" in record

    gh_stub.routes.pop("auth status")
    gh_stub.save()
    gh_stub.respond(f"pr view {PULL}", pull(isDraft=False))
    assert run_cli("sync", "github:1234").code == 0
    record = (github_ticket / "pulls.md").read_text(encoding="utf-8")
    assert "Refresh failed" not in record
    assert f"({PULL}) - open" in record


def test_a_failure_with_no_record_yet_writes_none(run_cli, github_ticket, gh_stub):
    gh_stub.fail("auth status", "You are not logged into any GitHub hosts.")

    result = run_cli("sync", "github:1234")

    assert result.code == 1
    assert not (github_ticket / "pulls.md").exists()


def test_a_url_that_is_no_pull_request_is_refused_before_anything_is_read(
    run_cli, github_ticket, gh_stub
):
    calls = len(gh_stub.calls)

    result = run_cli("sync", "github:1234", "--pull", "https://example.test/12")

    assert result.code == 1
    assert "is not the URL of a pull request" in result.err
    assert len(gh_stub.calls) == calls


REPOS = (
    "https://dev.azure.com/acme/billing-app/_apis/git/repositories/ledger/pullrequests"
)


def azure_pull(number: int = 31, **parts) -> dict:
    return {
        "pullRequestId": number,
        "status": "active",
        "isDraft": False,
        "reviewers": [],
        "repository": {"name": "ledger", "project": {"name": "billing-app"}},
        **parts,
    }


@pytest.mark.parametrize(
    ("parts", "status"),
    [
        ({"reviewers": [{"vote": 10}, {"vote": 0}]}, "open, approved"),
        ({"reviewers": [{"vote": 5}, {"vote": -5}]}, "open, waiting for author"),
        ({"reviewers": [{"vote": -10}, {"vote": 10}]}, "open, rejected"),
        ({"isDraft": True}, "draft"),
        ({"status": "completed", "reviewers": [{"vote": 10}]}, "merged"),
        ({"status": "abandoned"}, "closed"),
    ],
)
def test_pull_requests_on_azure_repos_are_found_from_the_workspace_branches(
    run_cli, bound, stub_work_item, az_stub, repository, sdlc_home, parts, status
):
    stub_work_item()
    assert run_cli("fetch", "ado:1234").code == 0
    probe(az_stub, 7)
    repository.git("checkout", "-b", BRANCH)
    repository.git(
        "remote",
        "set-url",
        "origin",
        "https://acme@dev.azure.com/acme/billing-app/_git/ledger",
    )
    write_plan(sdlc_home / ADO, ("ledger", BRANCH, repository.path))
    az_stub.respond(
        f"{REPOS}?searchCriteria.sourceRefName=refs/heads/{BRANCH}&searchCriteria.status=all",
        {"value": [azure_pull(**parts)], "count": 1},
    )

    result = run_cli("sync", "ado:1234")

    assert result.code == 0, result.err
    assert result.json["upstream"]["status"] == "unchanged"
    assert result.json["pulls"]["lines"] == [
        {
            "label": "billing-app/ledger!31",
            "url": "https://dev.azure.com/acme/billing-app/_git/ledger/pullrequest/31",
            "status": status,
        }
    ]


def test_a_recorded_azure_repos_pull_request_is_refreshed_by_its_url(
    run_cli, bound, stub_work_item, az_stub, sdlc_home
):
    stub_work_item()
    assert run_cli("fetch", "ado:1234").code == 0
    probe(az_stub, 7)
    url = "https://dev.azure.com/acme/billing-app/_git/ledger/pullrequest/31"
    az_stub.respond(f"{REPOS}/31", azure_pull(status="completed"))

    result = run_cli("sync", "ado:1234", "--pull", url)

    assert result.code == 0, result.err
    assert result.json["pulls"]["lines"] == [
        {"label": "billing-app/ledger!31", "url": url, "status": "merged"}
    ]


def test_a_local_ticket_has_nothing_upstream_and_still_records_its_pull_requests(
    run_cli, bound, make_ticket, write_config, on_github, gh_stub
):
    directory = make_ticket("acme", "billing-app", "local", "cache-ledger")
    write_config(
        "acme/billing-app/local/cache-ledger/ticket.json",
        {"source": "local", "id": "cache-ledger"},
    )
    write_plan(directory, ("billing-app", BRANCH, on_github.path))
    gh_stub.respond(f"pr list acme/billing-app {BRANCH}", [pull()])

    result = run_cli("sync", "local:cache-ledger")

    assert result.code == 0, result.err
    assert result.json["upstream"] == {
        "status": "local",
        "refreshed": False,
        "fields": [],
        "journal": [],
    }
    assert [line["url"] for line in result.json["pulls"]["lines"]] == [PULL]
