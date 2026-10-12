from pathlib import Path

import pytest

PLAN = """# Implementation Plan

## Workspace

### Scan roots

- `{root}` — given by the user

### Worktrees

| Repository | Branch | Kind | Path |
| ---------- | ------ | ---- | ---- |
{rows}

### Projects

| Project | Lives in | Path | Technology |
| ------- | -------- | ---- | ---------- |
| api | {label} | src/Api | .NET |

## Phase 1: Work

### Step 1.1

**Status:** Pending

**Target:** `src/Api/Invoice.cs` in `{label}`

**Artifacts:** [artifacts/step-1.1/README.md](artifacts/step-1.1/README.md)
"""


@pytest.fixture
def ticket(local_ticket):
    return local_ticket("Invoice export", "task")


def write_plan(ticket, repos, label=None):
    rows = "\n".join(
        f"| {repo.path.name} | {repo.git('branch', '--show-current')} | main | `{repo.path}` |"
        for repo in repos
    )
    ticket_dir = Path(ticket["paths"]["ticket_dir"])
    label = label or f"{repos[0].path.name}@{repos[0].git('branch', '--show-current')}"
    (ticket_dir / "plan.md").write_text(
        PLAN.format(root=repos[0].path.parent, rows=rows, label=label), encoding="utf-8"
    )
    step = ticket_dir / "artifacts" / "step-1.1"
    step.mkdir(parents=True, exist_ok=True)
    (step / "README.md").write_text(f"Edited in {label} at {repos[0].path}\n", encoding="utf-8")
    return ticket_dir


def adopt(run_cli, ticket, *extra):
    return run_cli("worktree", "adopt", ticket["ref"], *extra)


def test_a_protected_branch_worktree_is_refused_with_the_reason_and_the_offer(
    run_cli, ticket, repository
):
    write_plan(ticket, [repository])

    result = adopt(run_cli, ticket)

    assert result.code == 4
    report = result.json
    assert report["ok"] is False
    assert "protected branch" in report["worktrees"][0]["reason"]
    assert report["proposals"][0]["branch"] == f"feat/{ticket['id']}"


def test_a_workspace_on_a_current_ticket_branch_proceeds_without_an_offer(
    run_cli, ticket, repository
):
    repository.git("checkout", "-q", "-b", "feat/mine")
    write_plan(ticket, [repository])

    result = adopt(run_cli, ticket)

    assert result.code == 0
    assert result.json["ok"] is True
    assert result.json["proposals"] == []


def test_accepting_creates_a_worktree_and_rewrites_the_workspace(
    run_cli, ticket, repository
):
    ticket_dir = write_plan(ticket, [repository])

    result = adopt(run_cli, ticket, "--create")

    assert result.code == 0, result.err
    replaced = result.json["replaced"][0]
    new_path = replaced["new_path"]
    assert Path(new_path).is_dir()
    plan = (ticket_dir / "plan.md").read_text(encoding="utf-8")
    assert f"`{new_path}`" in plan
    assert f"{repository.path.name}@{replaced['new_branch']}" in plan
    assert "protected branch, so the work happens in" in plan


def test_no_stale_reference_survives_the_rewrite(run_cli, ticket, repository):
    ticket_dir = write_plan(ticket, [repository])
    old_path = str(repository.path)
    old_label = f"{repository.path.name}@main"

    adopt(run_cli, ticket, "--create")

    plan = (ticket_dir / "plan.md").read_text(encoding="utf-8")
    note = next(line for line in plan.splitlines() if line.startswith("> **"))
    body = plan.replace(note, "")
    artifact = (ticket_dir / "artifacts" / "step-1.1" / "README.md").read_text()
    assert old_label not in body + artifact
    assert f"`{old_path}`" not in body
    assert f"{old_path} " not in artifact


def test_the_new_worktree_is_a_current_ticket_branch_so_a_second_run_is_quiet(
    run_cli, ticket, repository
):
    write_plan(ticket, [repository])
    adopt(run_cli, ticket, "--create")

    again = adopt(run_cli, ticket)

    assert again.code == 0
    assert again.json["ok"] is True


def test_one_worktree_is_created_per_repository(run_cli, ticket, make_repository):
    first, second = make_repository("alpha"), make_repository("beta")
    write_plan(ticket, [first, second])

    result = adopt(run_cli, ticket, "--create")

    assert {r["repository"] for r in result.json["replaced"]} == {"alpha", "beta"}
    assert all(Path(r["new_path"]).is_dir() for r in result.json["replaced"])


def test_only_the_named_repositories_are_swapped(run_cli, ticket, make_repository):
    first, second = make_repository("alpha"), make_repository("beta")
    ticket_dir = write_plan(ticket, [first, second])

    result = adopt(run_cli, ticket, "--create", "--repo", str(first.path))

    assert [r["repository"] for r in result.json["replaced"]] == ["alpha"]
    assert f"`{second.path}`" in (ticket_dir / "plan.md").read_text(encoding="utf-8")


def test_a_ticket_with_no_plan_is_refused(run_cli, ticket):
    assert adopt(run_cli, ticket).code == 5
