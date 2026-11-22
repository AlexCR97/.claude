"""The protected-branch policy, through `guard check` and `guard protected`."""

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


def protected(run_cli, repository, *extra):
    return run_cli("guard", "protected", "--repo", str(repository.path), *extra)


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
    ("branch", "is_protected"),
    [("develop", True), ("release/1.2", True), ("releases", False), ("feat/x", False)],
)
def test_a_configured_pattern_protects_matching_branches(
    run_cli, write_config, repository, branch, is_protected
):
    write_config("sdlc.json", {"protected_branches": ["develop", "release/*"]})

    result = check(run_cli, repository, "commit", branch)

    assert result.json["protected"] is is_protected
    assert result.code == (4 if is_protected else 0)


def test_the_list_cascades_from_the_product_config(run_cli, write_config, repository):
    write_config("acme/web/product.json", {"protected_branches": ["develop"]})

    inside = check(run_cli, repository, "commit", "develop", "--context", "acme/web")
    outside = check(run_cli, repository, "commit", "develop")

    assert inside.code == 4
    assert outside.code == 0


def test_an_unknown_operation_is_an_error(run_cli, repository):
    assert check(run_cli, repository, "frobnicate").code == 1


def test_a_directory_outside_any_repository_is_an_error(run_cli, tmp_path):
    outside = tmp_path / "plain"
    outside.mkdir()

    result = run_cli("guard", "check", "--op", "edit", "--repo", str(outside))

    assert result.code == 1
    assert "not inside a git repository" in result.err


def test_an_edit_is_judged_by_the_branch_the_worktree_has_checked_out(
    run_cli, repository, tmp_path
):
    linked = tmp_path / "linked"
    repository.git("worktree", "add", "-q", "-b", "feat/1-thing", str(linked))

    in_main = run_cli("guard", "check", "--op", "edit", "--repo", str(repository.path))
    in_linked = run_cli("guard", "check", "--op", "edit", "--repo", str(linked))

    assert in_main.code == 4
    assert in_linked.code == 0
    assert in_linked.json["branch"] == "feat/1-thing"


def test_protected_lists_the_default_branch_and_the_configured_patterns(
    run_cli, write_config, repository
):
    write_config("sdlc.json", {"protected_branches": ["develop", "release/*"]})

    report = protected(run_cli, repository).json

    assert report["default_branch"] == "main"
    assert report["patterns"] == ["develop", "release/*"]
    assert report["protected_branches"] == ["main", "develop", "release/*"]
    assert report["branch"] == "main"
    assert report["protected"] is True


def test_protected_reports_whether_the_named_branch_is_protected(run_cli, repository):
    report = protected(run_cli, repository, "--branch", "feat/1-thing").json

    assert report["branch"] == "feat/1-thing"
    assert report["protected"] is False
    assert report["protected_branches"] == ["main"]


def test_protected_without_a_recorded_default_branch_lists_only_the_patterns(
    run_cli, write_config, tmp_path
):
    bare = tmp_path / "no-remote"
    bare.mkdir()
    git(bare, "init", "--initial-branch=main")
    write_config("sdlc.json", {"protected_branches": ["develop"]})

    result = run_cli("guard", "protected", "--repo", str(bare))

    assert result.code == 0
    assert result.json["default_branch"] is None
    assert result.json["protected_branches"] == ["develop"]
