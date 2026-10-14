from pathlib import Path

import pytest

from conftest import git


@pytest.fixture
def ticket(local_ticket):
    return local_ticket("Invoice export", "task")


def survey(run_cli, ticket, repository):
    result = run_cli("worktree", "survey", ticket["ref"], "--repo", str(repository.path))
    assert result.code == 0, result.err
    return result.json["repositories"][0]


def advance_remote(repository, name="ahead.txt"):
    clone = repository.path.parent / f"clone-{name}"
    git(repository.path.parent, "clone", "-q", str(repository.remote), str(clone))
    git(clone, "config", "user.email", "o@example.com")
    git(clone, "config", "user.name", "Other")
    (clone / name).write_text("a", encoding="utf-8")
    git(clone, "add", name)
    git(clone, "commit", "-q", "-m", name)
    git(clone, "push", "-q", "origin", "main")


def by_branch(report, branch):
    return next(w for w in report["worktrees"] if w["branch"] == branch)


def test_an_up_to_date_main_worktree_is_current_and_protected(run_cli, ticket, repository):
    report = survey(run_cli, ticket, repository)

    main = by_branch(report, "main")
    assert (main["status"], main["behind"], main["protected"]) == ("current", 0, True)


def test_the_survey_fetches_so_a_stale_worktree_is_reported_behind(
    run_cli, ticket, repository
):
    advance_remote(repository)
    advance_remote(repository, "again.txt")

    main = by_branch(survey(run_cli, ticket, repository), "main")

    assert (main["status"], main["behind"]) == ("behind", 2)


def test_planning_against_main_leaves_it_unchanged(run_cli, ticket, repository):
    advance_remote(repository)
    head = repository.git("rev-parse", "HEAD")

    survey(run_cli, ticket, repository)

    assert repository.git("rev-parse", "HEAD") == head
    assert repository.git("status", "--porcelain") == ""


def test_a_diverged_branch_is_reported_as_diverged(run_cli, ticket, repository):
    repository.git("checkout", "-q", "-b", "feat/old")
    repository.commit("mine.txt")
    advance_remote(repository)

    report = survey(run_cli, ticket, repository)

    branch = by_branch(report, "feat/old")
    assert branch["status"] == "diverged"
    assert (branch["ahead"], branch["behind"]) == (1, 1)


def test_the_offer_is_made_when_only_main_exists(run_cli, ticket, repository):
    report = survey(run_cli, ticket, repository)

    assert report["offer"] is True
    assert report["proposal"]["branch"] == f"feat/{ticket['id']}"


def test_the_offer_is_made_when_the_only_ticket_branch_is_stale(
    run_cli, ticket, repository
):
    repository.git("checkout", "-q", "-b", "feat/old")
    advance_remote(repository)

    assert survey(run_cli, ticket, repository)["offer"] is True


def test_no_offer_when_a_current_ticket_branch_exists(run_cli, ticket, repository):
    repository.git("checkout", "-q", "-b", "feat/current")
    repository.commit("work.txt")

    report = survey(run_cli, ticket, repository)

    assert report["offer"] is False
    assert "proposal" not in report


def test_a_current_ticket_worktree_makes_no_offer(run_cli, ticket, repository):
    created = run_cli(
        "worktree", "create", ticket["ref"], "--repo", str(repository.path)
    ).json["created"][0]

    report = survey(run_cli, ticket, repository)

    assert report["offer"] is False
    assert by_branch(report, created["branch"])["status"] == "current"


def test_a_prunable_worktree_is_skipped(run_cli, ticket, repository, tmp_path):
    gone = tmp_path / "gone"
    repository.git("worktree", "add", "-q", "-b", "feat/gone", str(gone))
    import shutil

    shutil.rmtree(gone)

    report = survey(run_cli, ticket, repository)

    assert all(w["branch"] != "feat/gone" for w in report["worktrees"])
