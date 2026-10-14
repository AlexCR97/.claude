import json
from pathlib import Path

import pytest

from conftest import git


@pytest.fixture
def ticket(local_ticket):
    return local_ticket("Invoice export", "user-story")


def worktree_cmd(run_cli, action, ticket, *repos, extra=()):
    args = ["worktree", action, ticket["ref"]]
    for repo in repos:
        args += ["--repo", str(repo.path)]
    return run_cli(*args, *extra)


@pytest.mark.parametrize(
    ("ticket_type", "prefix"),
    [("user-story", "feat"), ("task", "feat"), ("bug", "fix"), ("spike", "spike"), ("tech-debt", "chore")],
)
def test_the_branch_prefix_follows_the_ticket_type(
    run_cli, local_ticket, repository, ticket_type, prefix
):
    ticket = local_ticket("Invoice export", ticket_type)

    plan = worktree_cmd(run_cli, "propose", ticket, repository).json

    assert plan["branch"] == f"{prefix}/{ticket['id']}"


def test_the_branch_is_named_from_the_id_and_title(run_cli, repository):
    result = run_cli(
        "new", "--source", "local", "--title", "Invoice export!", "--id", "18692",
        "--type", "user-story",
    )
    ticket = result.json

    plan = worktree_cmd(run_cli, "propose", ticket, repository).json

    assert plan["branch"] == "feat/18692-invoice-export"


def test_proposing_changes_nothing(run_cli, ticket, repository):
    worktree_cmd(run_cli, "propose", ticket, repository)

    assert not (repository.path / ".worktrees").exists()
    assert "feat" not in repository.git("branch", "--list", "feat/*")


def test_the_worktree_is_created_inside_the_repository_from_the_remote_default(
    run_cli, ticket, repository
):
    result = worktree_cmd(run_cli, "create", ticket, repository, extra=["--add-ignore"])

    assert result.code == 0, result.err
    created = result.json["created"][0]
    worktree = Path(created["worktree"])
    assert worktree.parent == (repository.path / ".worktrees").resolve()
    assert git(worktree, "branch", "--show-current") == created["branch"]
    assert git(worktree, "rev-parse", "HEAD") == repository.git("rev-parse", "origin/main")


def test_the_branch_is_cut_from_the_remote_not_a_stale_local_default(
    run_cli, ticket, repository, tmp_path
):
    clone = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(repository.remote), str(clone))
    git(clone, "config", "user.email", "o@example.com")
    git(clone, "config", "user.name", "Other")
    (clone / "new.txt").write_text("n", encoding="utf-8")
    git(clone, "add", "new.txt")
    git(clone, "commit", "-q", "-m", "ahead")
    git(clone, "push", "-q", "origin", "main")

    created = worktree_cmd(run_cli, "create", ticket, repository).json["created"][0]

    assert (Path(created["worktree"]) / "new.txt").is_file()


def test_worktree_root_moves_the_worktree_out_of_the_repository(
    run_cli, tickets_home, tmp_path, ticket, repository
):
    root = tmp_path / "elsewhere"
    (tickets_home / "config.json").write_text(
        json.dumps({"worktree_root": str(root)}), encoding="utf-8"
    )

    created = worktree_cmd(run_cli, "create", ticket, repository).json["created"][0]

    assert Path(created["worktree"]).is_relative_to(root.resolve())
    assert created["ignore_offer"] is None


def test_a_missing_ignore_entry_is_offered_and_never_added_silently(
    run_cli, ticket, repository
):
    plan = worktree_cmd(run_cli, "propose", ticket, repository).json["plans"][0]
    assert plan["ignore_offer"]["entry"] == "/.worktrees/"

    created = worktree_cmd(run_cli, "create", ticket, repository).json["created"][0]

    assert created["ignore_offer"] is not None
    assert not (repository.path / ".gitignore").exists()


def test_accepting_the_offer_adds_the_entry(run_cli, ticket, repository):
    worktree_cmd(run_cli, "create", ticket, repository, extra=["--add-ignore"])

    assert "/.worktrees/" in (repository.path / ".gitignore").read_text()
    assert ".worktrees" not in repository.git("status", "--porcelain").replace(".gitignore", "")


def test_an_already_ignored_directory_makes_no_offer(run_cli, ticket, repository):
    repository.commit(".gitignore", ".worktrees/\n")

    plan = worktree_cmd(run_cli, "propose", ticket, repository).json["plans"][0]

    assert plan["ignore_offer"] is None


def test_one_worktree_is_created_per_repository(
    run_cli, ticket, make_repository
):
    first, second = make_repository("alpha"), make_repository("beta")

    created = worktree_cmd(run_cli, "create", ticket, first, second).json["created"]

    assert len(created) == 2
    assert {Path(c["repository"]).name for c in created} == {"alpha", "beta"}
    assert all(Path(c["worktree"]).is_dir() for c in created)


def test_a_configured_pattern_that_catches_the_ticket_branch_refuses_everything(
    run_cli, tickets_home, ticket, make_repository
):
    (tickets_home / "config.json").write_text(
        json.dumps({"protected_branches": ["feat/*"]}), encoding="utf-8"
    )
    first, second = make_repository("alpha"), make_repository("beta")

    result = worktree_cmd(run_cli, "create", ticket, first, second)

    assert result.code == 4
    assert not (first.path / ".worktrees").exists()
    assert not (second.path / ".worktrees").exists()


def test_creating_again_reuses_the_existing_worktree(run_cli, ticket, repository):
    first = worktree_cmd(run_cli, "create", ticket, repository).json["created"][0]

    second = worktree_cmd(run_cli, "create", ticket, repository).json["created"][0]

    assert second["created"] is False
    assert second["worktree"] == first["worktree"]


def test_a_repository_without_origin_head_is_an_error(run_cli, ticket, tmp_path):
    bare = tmp_path / "plain"
    bare.mkdir()
    git(bare, "init", "-q")

    class Plain:
        path = bare

    assert worktree_cmd(run_cli, "propose", ticket, Plain).code == 1
