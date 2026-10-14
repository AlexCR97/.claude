import json

import pytest

from conftest import git

ALLOWED = ["fetch", "fast-forward", "log", "diff", "blame", "show", "cherry-pick-from"]
FORBIDDEN = [
    "commit",
    "push",
    "force-push",
    "merge",
    "rebase",
    "reset",
    "revert",
    "cherry-pick",
    "edit",
]


def check(run_cli, repository, op, branch=None, *extra):
    args = ["guard", "check", "--op", op, "--repo", str(repository.path), *extra]
    if branch:
        args += ["--branch", branch]
    return run_cli(*args)


@pytest.mark.parametrize("op", ALLOWED)
def test_reads_and_fast_forwards_are_allowed_on_the_default_branch(
    run_cli, repository, op
):
    result = check(run_cli, repository, op)

    assert result.code == 0
    assert result.json["protected"] is True
    assert result.json["allowed"] is True


@pytest.mark.parametrize("op", FORBIDDEN)
def test_writes_are_refused_on_the_default_branch_with_the_reason(
    run_cli, repository, op
):
    result = check(run_cli, repository, op)

    assert result.code == 4
    assert result.json["allowed"] is False
    assert "protected branch" in result.json["reason"]


@pytest.mark.parametrize("op", FORBIDDEN)
def test_every_operation_is_allowed_on_an_unprotected_branch(run_cli, repository, op):
    repository.git("checkout", "-q", "-b", "feat/1-thing")

    result = check(run_cli, repository, op)

    assert result.code == 0
    assert result.json["protected"] is False


def test_the_default_branch_comes_from_origin_head_not_its_name(
    run_cli, make_repository
):
    repository = make_repository()
    repository.git("checkout", "-q", "-b", "trunk")
    repository.git("push", "-q", "origin", "trunk")
    repository.git("remote", "set-head", "origin", "trunk")

    assert check(run_cli, repository, "commit", "trunk").code == 4
    assert check(run_cli, repository, "commit", "main").code == 0


@pytest.mark.parametrize(
    ("branch", "protected"),
    [("develop", True), ("release/1.2", True), ("releases", False), ("feat/x", False)],
)
def test_a_configured_pattern_protects_matching_branches(
    run_cli, tickets_home, repository, branch, protected
):
    (tickets_home / "config.json").write_text(
        json.dumps({"protected_branches": ["develop", "release/*"]}), encoding="utf-8"
    )

    result = check(run_cli, repository, "commit", branch)

    assert result.json["protected"] is protected
    assert result.code == (4 if protected else 0)


def test_the_list_cascades_from_the_product_config(
    run_cli, tickets_home, repository
):
    product = tickets_home / "acme" / "web"
    product.mkdir(parents=True)
    (product / "config.json").write_text(
        json.dumps({"protected_branches": ["develop"]}), encoding="utf-8"
    )

    inside = check(run_cli, repository, "commit", "develop", "--in", "acme/web")
    outside = check(run_cli, repository, "commit", "develop")

    assert inside.code == 4
    assert outside.code == 0


def test_an_unknown_operation_is_an_error(run_cli, repository):
    assert check(run_cli, repository, "frobnicate").code == 1


def push_remote_commit(make_repository, repository, name="remote.txt"):
    """Advance origin/main from a second clone."""
    clone = repository.path.parent / "other-clone"
    git(repository.path.parent, "clone", "-q", str(repository.remote), str(clone))
    git(clone, "config", "user.email", "o@example.com")
    git(clone, "config", "user.name", "Other")
    (clone / name).write_text("r", encoding="utf-8")
    git(clone, "add", name)
    git(clone, "commit", "-q", "-m", "remote")
    git(clone, "push", "-q", "origin", "main")


def fast_forward(run_cli, repository):
    return run_cli(
        "guard", "fast-forward", "--branch", "main", "--repo", str(repository.path)
    )


def test_a_clean_branch_strictly_behind_is_fast_forwarded(
    run_cli, make_repository, repository
):
    push_remote_commit(make_repository, repository)

    result = fast_forward(run_cli, repository)

    assert result.code == 0, result.err
    assert result.json["updated"] is True
    assert (repository.path / "remote.txt").is_file()


def test_a_branch_already_current_is_left_alone(run_cli, repository):
    result = fast_forward(run_cli, repository)

    assert result.code == 0
    assert result.json["updated"] is False


def test_a_dirty_tree_refuses_the_fast_forward_and_says_why(
    run_cli, make_repository, repository
):
    push_remote_commit(make_repository, repository)
    (repository.path / "README.md").write_text("edited", encoding="utf-8")
    head = repository.git("rev-parse", "HEAD")

    result = fast_forward(run_cli, repository)

    assert result.code == 4
    assert "uncommitted" in result.json["reason"]
    assert repository.git("rev-parse", "HEAD") == head


def test_local_only_commits_refuse_the_fast_forward(run_cli, repository):
    repository.commit("local.txt")

    result = fast_forward(run_cli, repository)

    assert result.code == 4
    assert "local-only" in result.json["reason"]


def test_a_diverged_branch_refuses_the_fast_forward(
    run_cli, make_repository, repository
):
    push_remote_commit(make_repository, repository)
    repository.commit("local.txt")

    result = fast_forward(run_cli, repository)

    assert result.code == 4
    assert "diverged" in result.json["reason"]


def test_a_branch_checked_out_nowhere_is_fast_forwarded_without_a_worktree(
    run_cli, make_repository, repository
):
    push_remote_commit(make_repository, repository)
    repository.git("checkout", "-q", "-b", "other")

    result = fast_forward(run_cli, repository)

    assert result.code == 0
    assert repository.git("rev-parse", "main") == repository.git(
        "rev-parse", "origin/main"
    )
