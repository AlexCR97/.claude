# Git policy — the protected-branch guard

Read by every `ticket-*` skill that runs git. The policy is enforced by one module, `ticketlib/guard.py`, reached through the resolver. A skill asks it rather than restating the rule here or in its own words. The reasoning is in [ADR 0001](../../docs/adr/0001-protected-branches-are-read-and-fast-forward-only.md).

## What is protected

The repository's **default branch** (what `origin/HEAD` names) and any branch matching a pattern in `protected_branches`, a list in the effective config that cascades root, namespace, product and is empty by default. Patterns may use `*`.

## What a skill may do

Any git or `gh` operation, except one that writes to a protected branch.

| On a protected branch | |
| --- | --- |
| Allowed | `fetch`, `log`, `diff`, `blame`, `show`, cherry-picking a commit **from** it, and fast-forwarding it from its remote |
| Refused | `commit`, `push`, `force-push`, a merge that is not a fast-forward, `rebase`, `reset`, `revert`, cherry-picking **onto** it, and editing files in a worktree that has it checked out |

On any other branch every operation is allowed, but **committing and pushing happen only when the developer asks.** A skill never decides on its own to commit, push or open a pull request.

## Asking the guard

```bash
python "{skills}/ticket-common/ticket.py" guard check --op {operation} [--branch {branch}] [--repo {directory}] [--in {namespace/product}]
```

Exit `0` allows it. Exit `4` refuses it, and `reason` says why — report that reason and stop; never look for another way to do the same thing. Without `--branch` it checks the repository's current branch. Run it before any operation that could write, and before editing a file in a worktree (`--op edit`).

```bash
python "{skills}/ticket-common/ticket.py" guard fast-forward --branch {branch} [--repo {directory}]
```

Fetches, then brings a local branch up to its remote when that loses nothing. It refuses, saying why, when the worktree holding the branch has uncommitted changes, when the branch has commits the remote lacks, or when the two diverged.

`guard protected` reports whether a branch is protected and which patterns apply.
