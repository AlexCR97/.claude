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


def init_without_remote(path, branch: str, *, commit: bool = False):
    path.mkdir()
    git(path, "init", f"--initial-branch={branch}")
    if commit:
        git(path, "config", "user.email", "test@example.com")
        git(path, "config", "user.name", "Test")
        git(path, "config", "commit.gpgsign", "false")
        (path / "README.md").write_text("x", encoding="utf-8")
        git(path, "add", "README.md")
        git(path, "commit", "-m", "init")
    return path


def test_the_default_branch_names_where_it_came_from(run_cli, repository):
    verdict = check(run_cli, repository, "commit", "main")
    report = protected(run_cli, repository).json

    assert verdict.json["default_branch_source"] == "origin/HEAD"
    assert report["default_branch_source"] == "origin/HEAD"


@pytest.mark.parametrize("name", ["main", "master"])
def test_without_origin_head_the_one_local_main_or_master_is_still_protected(
    run_cli, make_repository, name
):
    repository = make_repository()
    if name != "main":
        repository.git("branch", "-m", "main", name)
    repository.git("remote", "set-head", "origin", "-d")
    repository.git("checkout", "-q", "-b", "feat/1-thing")

    verdict = check(run_cli, repository, "commit", name)

    assert verdict.code == 4
    assert verdict.json["protected"] is True
    assert verdict.json["default_branch_source"] == "inferred"
    assert protected(run_cli, repository).json["default_branch"] == name


def test_without_origin_head_the_checked_out_main_is_protected_when_both_names_exist(
    run_cli, make_repository
):
    repository = make_repository()
    repository.git("remote", "set-head", "origin", "-d")
    repository.git("branch", "master")

    on_main = check(run_cli, repository, "commit")
    repository.git("checkout", "-q", "-b", "feat/1-thing")
    on_feature = check(run_cli, repository, "commit")

    assert on_main.code == 4
    assert on_main.json["default_branch_source"] == "inferred"
    assert on_feature.code == 0
    assert on_feature.json["default_branch_source"] == "unknown"


def test_a_repository_with_no_commits_on_main_infers_it_from_the_checked_out_branch(
    run_cli, tmp_path
):
    path = init_without_remote(tmp_path / "fresh", "main")

    result = run_cli("guard", "check", "--op", "commit", "--repo", str(path))

    assert result.code == 4
    assert result.json["default_branch_source"] == "inferred"


def test_a_default_branch_that_cannot_be_determined_is_said_so_and_only_patterns_apply(
    run_cli, write_config, tmp_path
):
    path = init_without_remote(tmp_path / "odd", "trunk", commit=True)
    write_config("sdlc.json", {"protected_branches": ["release/*"]})

    plain = run_cli("guard", "check", "--op", "commit", "--repo", str(path))
    listed = run_cli("guard", "protected", "--repo", str(path))
    pattern = run_cli(
        "guard", "check", "--op", "commit", "--repo", str(path), "--branch", "release/1"
    )

    assert plain.code == 0
    assert plain.json["default_branch_source"] == "unknown"
    assert listed.json["default_branch"] is None
    assert listed.json["default_branch_source"] == "unknown"
    assert listed.json["protected_branches"] == ["release/*"]
    assert pattern.code == 4
