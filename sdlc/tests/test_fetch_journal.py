"""`fetch` mirrors a remote ticket's journal: each marked comment upstream becomes a file in `journal/`."""

from pathlib import Path

import pytest

GITHUB = "acme/billing-app/github/1234"
ADO = "acme/billing-app/ado/1234"
ADO_BOTH = ["--coordinate", "organization=acme", "--coordinate", "project=billing-app"]

ENTRY = "# Journal entry - [#1234: Cache the ledger lookup](https://example.test)\n\n**Next:** write the cache test\n"


def posted(name: str, entry: str = ENTRY) -> str:
    return f"sdlc-journal-entry `{name}`\n\n{entry}"


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


@pytest.fixture
def github_with_comments(stub_issue):
    def register(*bodies: str) -> None:
        stub_issue(
            comments=[
                {"id": number, "body": body, "user": {"login": "pablo"}}
                for number, body in enumerate(bodies, start=1)
            ]
        )

    return register


def journal_of(sdlc_home: Path, ticket: str) -> dict[str, str]:
    directory = sdlc_home / ticket / "journal"
    if not directory.is_dir():
        return {}
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(directory.iterdir())
    }


def test_a_marked_github_comment_becomes_a_journal_file_named_by_its_marker(
    run_cli, bound, github_with_comments, sdlc_home
):
    github_with_comments(posted("2026-11-23T14-05-09Z.md"))

    result = run_cli("fetch", "github:1234")

    assert result.code == 0, result.err
    assert journal_of(sdlc_home, GITHUB) == {"2026-11-23T14-05-09Z.md": ENTRY}


@pytest.fixture
def ado_with_comments(stub_work_item):
    def register(*texts: str) -> None:
        stub_work_item(
            comments=[
                {
                    "id": number,
                    "text": text,
                    "format": "markdown",
                    "createdBy": {"displayName": "Pablo", "uniqueName": "pablo@acme"},
                }
                for number, text in enumerate(texts, start=1)
            ]
        )

    return register


def test_a_marked_work_item_comment_becomes_a_journal_file_named_by_its_marker(
    run_cli, bound, ado_with_comments, sdlc_home
):
    ado_with_comments(posted("2026-11-23T14-05-09Z.md"))

    result = run_cli("fetch", "ado:1234", *ADO_BOTH)

    assert result.code == 0, result.err
    assert journal_of(sdlc_home, ADO) == {"2026-11-23T14-05-09Z.md": ENTRY}


@pytest.fixture(params=["github", "ado"])
def source(request, github_with_comments, ado_with_comments):
    """One remote ticket, from either source: register its comments, fetch it, find its directory."""

    class Source:
        name = request.param
        ticket = GITHUB if request.param == "github" else ADO
        arguments = (
            ["fetch", "github:1234"]
            if request.param == "github"
            else ["fetch", "ado:1234", *ADO_BOTH]
        )

        @staticmethod
        def comments(*texts: str) -> None:
            register = (
                github_with_comments if request.param == "github" else ado_with_comments
            )
            register(*texts)

    return Source


def test_comments_without_the_marker_on_their_first_line_are_not_journal_entries(
    run_cli, bound, source, sdlc_home
):
    source.comments(
        "Which cache?",
        "Quoting it: sdlc-journal-entry `2026-11-23T14-05-09Z.md`",
        "sdlc-journal-entry `2026-11-23T14-05-09Z.md` and then some",
        "sdlc-journal-entry `../../escape.md`\n\n# Not an entry",
    )

    result = run_cli(*source.arguments)

    assert result.code == 0, result.err
    assert journal_of(sdlc_home, source.ticket) == {}


def test_an_existing_journal_file_is_never_overwritten(
    run_cli, bound, source, sdlc_home
):
    source.comments(
        posted("2026-11-23T14-05-09Z.md", "# Upstream's copy\n"),
        posted("2026-11-24T09-00-00Z.md"),
    )
    journal = sdlc_home / source.ticket / "journal"
    journal.mkdir(parents=True)
    (journal / "2026-11-23T14-05-09Z.md").write_text("# Mine\n", encoding="utf-8")

    result = run_cli(*source.arguments)

    assert result.code == 0, result.err
    assert journal_of(sdlc_home, source.ticket) == {
        "2026-11-23T14-05-09Z.md": "# Mine\n",
        "2026-11-24T09-00-00Z.md": ENTRY,
    }
    assert result.json["fetched"]["journal"] == {
        "written": ["2026-11-24T09-00-00Z.md"],
        "kept": ["2026-11-23T14-05-09Z.md"],
    }


def test_a_marker_is_read_through_surrounding_whitespace_and_crlf(
    run_cli, bound, source, sdlc_home
):
    source.comments(
        "﻿\r\n  sdlc-journal-entry `2026-11-23T14-05-09Z.md`  \r\n\r\n"
        + ENTRY.replace("\n", "\r\n")
        + "\r\n\r\n"
    )

    result = run_cli(*source.arguments)

    assert result.code == 0, result.err
    assert journal_of(sdlc_home, source.ticket) == {"2026-11-23T14-05-09Z.md": ENTRY}


def test_an_entry_posted_twice_is_mirrored_once_from_its_first_comment(
    run_cli, bound, source, sdlc_home
):
    source.comments(
        posted("2026-11-23T14-05-09Z.md"),
        posted("2026-11-23T14-05-09Z.md", "# A later duplicate\n"),
    )

    run_cli(*source.arguments)

    assert journal_of(sdlc_home, source.ticket) == {"2026-11-23T14-05-09Z.md": ENTRY}


def test_a_refresh_with_nothing_new_upstream_leaves_the_journal_as_it_was(
    run_cli, bound, source, sdlc_home
):
    source.comments(posted("2026-11-23T14-05-09Z.md"))
    run_cli(*source.arguments)

    result = run_cli(*source.arguments)

    assert result.json["fetched"]["journal"] == {
        "written": [],
        "kept": ["2026-11-23T14-05-09Z.md"],
    }


def checkpoint_here(sdlc_home: Path, ticket: str, name: str) -> None:
    """What `checkpoint` leaves on this machine: the entry's file, whose comment it posted upstream."""
    journal = sdlc_home / ticket / "journal"
    journal.mkdir(parents=True, exist_ok=True)
    (journal / name).write_text(ENTRY, encoding="utf-8")


def test_a_github_issue_changed_only_by_this_machines_own_entries_says_only_the_journal_moved(
    run_cli, bound, github_with_comments, sdlc_home
):
    github_with_comments("Which cache?", posted("2026-11-23T14-05-09Z.md"))
    run_cli("fetch", "github:1234")
    checkpoint_here(sdlc_home, GITHUB, "2026-11-24T09-00-00Z.md")
    github_with_comments(
        "Which cache?",
        posted("2026-11-23T14-05-09Z.md"),
        posted("2026-11-24T09-00-00Z.md"),
    )

    report = run_cli("fetch", "github:1234", "--check").json

    assert report["status"] == "journal_only"
    assert report["journal"] == {
        "upstream": ["2026-11-23T14-05-09Z.md", "2026-11-24T09-00-00Z.md"],
        "unmirrored": [],
    }


def test_an_entry_another_machine_posted_is_reported_unmirrored_in_full_with_its_author(
    run_cli, bound, github_with_comments, sdlc_home
):
    github_with_comments(posted("2026-11-23T14-05-09Z.md"))
    run_cli("fetch", "github:1234")
    elsewhere = "# Journal entry - elsewhere\n\n**Next:** wire the cache\n"
    github_with_comments(
        posted("2026-11-23T14-05-09Z.md"), posted("2026-11-25T10-00-00Z.md", elsewhere)
    )

    report = run_cli("fetch", "github:1234", "--check").json

    assert report["status"] == "journal_unmirrored"
    assert report["journal"]["unmirrored"] == ["2026-11-25T10-00-00Z.md"]
    assert report["journal"]["newest_unmirrored"] == {
        "name": "2026-11-25T10-00-00Z.md",
        "entry": elsewhere,
        "author": "pablo",
    }
    assert journal_of(sdlc_home, GITHUB) == {"2026-11-23T14-05-09Z.md": ENTRY}


def test_a_github_issue_with_a_new_human_comment_beside_an_entry_is_more_than_the_journal(
    run_cli, bound, github_with_comments, sdlc_home
):
    github_with_comments()
    run_cli("fetch", "github:1234")
    checkpoint_here(sdlc_home, GITHUB, "2026-11-24T09-00-00Z.md")
    github_with_comments(posted("2026-11-24T09-00-00Z.md"), "Use Redis, not memcached.")

    report = run_cli("fetch", "github:1234", "--check").json

    assert report["status"] == "changed"


ADO_ITEM = "https://dev.azure.com/acme/_apis/wit/workItems/1234"


def ado_comment(number: int, text: str) -> dict:
    return {"id": number, "text": text, "createdBy": {"displayName": "Pablo"}}


def test_a_work_item_whose_rev_moved_only_for_this_machines_entry_says_only_the_journal_moved(
    run_cli, bound, stub_work_item, az_stub, sdlc_home
):
    stub_work_item(
        rev=7,
        fields={"System.ChangedDate": "2026-11-23T10:00:00Z", "System.CommentCount": 0},
    )
    run_cli("fetch", "ado:1234", *ADO_BOTH)
    checkpoint_here(sdlc_home, ADO, "2026-11-24T09-00-00Z.md")
    stub_work_item(
        rev=8,
        fields={"System.ChangedDate": "2026-11-24T09:00:05Z", "System.CommentCount": 1},
        comments=[ado_comment(1, posted("2026-11-24T09-00-00Z.md"))],
    )
    az_stub.respond(f"{ADO_ITEM}?fields=System.Rev", {"id": 1234, "rev": 8})

    report = run_cli("fetch", "ado:1234", "--check").json

    assert report["status"] == "journal_only"
    assert report["live"] == {"rev": 8}
    assert report["journal"] == {
        "upstream": ["2026-11-24T09-00-00Z.md"],
        "unmirrored": [],
    }


def test_a_work_item_retitled_beside_an_entry_is_more_than_the_journal(
    run_cli, bound, stub_work_item, az_stub, sdlc_home
):
    stub_work_item(rev=7)
    run_cli("fetch", "ado:1234", *ADO_BOTH)
    checkpoint_here(sdlc_home, ADO, "2026-11-24T09-00-00Z.md")
    stub_work_item(
        rev=9,
        fields={"System.Title": "Cache the ledger lookup in Redis"},
        comments=[ado_comment(1, posted("2026-11-24T09-00-00Z.md"))],
    )
    az_stub.respond(f"{ADO_ITEM}?fields=System.Rev", {"id": 1234, "rev": 9})

    report = run_cli("fetch", "ado:1234", "--check").json

    assert report["status"] == "changed"


def test_an_unmoved_ticket_whose_mirror_holds_an_entry_journal_lacks_reads_journal_unmirrored(
    run_cli, bound, source, sdlc_home, az_stub
):
    source.comments(posted("2026-11-23T14-05-09Z.md"))
    run_cli(*source.arguments)
    (sdlc_home / source.ticket / "journal" / "2026-11-23T14-05-09Z.md").unlink()
    az_stub.respond(f"{ADO_ITEM}?fields=System.Rev", {"id": 1234, "rev": 7})

    report = run_cli("fetch", f"{source.name}:1234", "--check").json

    assert report["status"] == "journal_unmirrored"
    assert report["changed"] is False
    assert report["journal"]["unmirrored"] == ["2026-11-23T14-05-09Z.md"]
    assert report["journal"]["newest_unmirrored"]["entry"] == ENTRY
