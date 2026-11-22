# Guard

The protected-branch policy and the naming of ticket branches and worktrees. The policy is enforced by the `guard` verb, so one definition of "protected" covers every skill; the reasons are in [ADR 0001](../docs/adr/0001-protected-branches-are-read-and-fast-forward-only.md).

## What is protected

The repository's **default branch** (what `origin/HEAD` names) and any branch matching a pattern in `protected_branches` in the effective config (empty by default; `*` matches). `guard protected` lists them.

## Policy

| On a protected branch | Operations |
| --- | --- |
| Allowed | `fetch`, `log`, `diff`, `blame`, `show`, `cherry-pick-from` (a commit taken from it) and `fast-forward` |
| Refused | `commit`, `push`, `force-push`, `merge`, `rebase`, `reset`, `revert`, `cherry-pick` (onto it) and `edit` (changing files in a worktree that has it checked out) |

On any other branch every operation is allowed, but commit and push only when the developer asks. A skill never decides on its own to commit, push or open a pull request.

## Asking the guard

```
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" guard check --op <operation> [--repo <directory>] [--branch <name>] [--context <namespace>[/<product>]]
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" guard protected [--repo <directory>] [--branch <name>] [--context <namespace>[/<product>]]
```

- `check` exits `0` when the operation is allowed and `4` when refused; `reason` says why. Report a refusal and stop: never look for another way to do the same thing.
- Without `--branch` the branch checked out in `--repo` is judged, so `--repo <worktree>` with `--op edit` answers whether that worktree may be edited. `--repo` takes any directory inside the repository.
- Pass `--context` when the session has one, so its `protected_branches` apply.
- The guard never runs git. A fast-forward is `git fetch`, then `git merge --ff-only origin/<branch>` in the worktree that holds the branch, run only after `check --op fast-forward` allows it and only when that worktree is clean.

## Ticket branches and worktrees

- **Branch**: `{prefix}/{id}-{title-slug}`. The prefix is `feat` for a `user-story` or `task`, `fix` for a `bug`, `spike` for a `spike` and `chore` for `tech-debt`. At most **28 characters**: cut the title slug back to its leading whole words that fit, as in `feat/18159-invoice-export`. A branch name is a label; never infer a ticket from it.
- **Base**: cut from `origin/{default branch}` after a `git fetch`, never from a local default branch that may be behind. Create it with `--no-track`, so that it does not take the default branch as its upstream.
- **Worktree**: a directory named after the branch with `/` as `-` (so also at most 28 characters), under `{repository}/.worktrees/`, or under `{worktree_root}/{repository}/` when the effective config sets `worktree_root`. Reuse an existing worktree of the branch.
- **`.worktrees/` is assumed git-ignored.** When it is not, offer to add it to the repository's ignore file and add it only on a yes.
- **Never create a ticket branch whose name matches a protected pattern.**
