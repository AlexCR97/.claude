---
name: commit
description: Commits a phase's or session's changes, staging only those files, with a conventional message that links the sdlc ticket when there is one. Use when asked to commit work on an sdlc ticket, or to commit with sdlc.
argument-hint: "[<ticket reference>] [<phase>] [push] [ship]"
---

# Commit

Commit the changes of the phase or session `$ARGUMENTS` points to, with or without an sdlc ticket: one commit per repository the changes span. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The protected-branch policy is `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The ticket**, optional: a reference, resolved with `resolve <reference>` (adding `--context {namespace}[/{product}]` when the session has one). No reference: the ticket this session has been working on, else ask once, with "no ticket" as an option. Never infer the ticket from the branch name. With a ticket, read its `source`, `id`, `type` and `coordinates` from `ticket.json`, and its `plan.md` when there is one.
- **The phase**, if named: its number in the ticket's `plan.md`. Otherwise the changes are the session's.
- **`push`**: push the commit afterwards. Without it, and outside a ship run, the commit stays local.
- **`ship`**: the [ship flag](../../shared/conventions.md#ship-runs). It waives the confirmation before committing and implies `push` ([ADR 0008](../../docs/adr/0008-a-ship-run-may-commit-push-and-open-pull-requests.md)); nothing here is a hard stop.

## The changes

The **change set** is the files the phase or the session changed, in each worktree and plain directory the plan's Workspace lists (no plan: the invocation directory's repository). The phase's step targets and the edits this conversation made name them; `/sdlc:document` edits made for the same projects belong with them. Read `git status --porcelain` in each repository and match it against the change set:

- A changed file outside the change set stays out. Name it, so the user knows it was left.
- A file in the change set that git shows unchanged has nothing to commit.
- Nothing left in any repository: say so and stop.

**Secret-looking files are refused**: any file that looks like it holds a credential, judged by its name and its diff. Examples, not the whole list: `.env` and `.env.*`, keys and certificates (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`), `credentials.*` and `secrets.*`, a name holding `secret` or `password`, and a diff adding what looks like a private key, token or password. A template holding no values, such as `.env.example`, is not one. A refused file leaves the change set; name it and why. The user commits a false positive by hand.

## The guard

For each repository with changes, ask `guard check --op commit --repo <worktree directory>`, with `--context` when the session has one. A refusal is final: report its `reason` and stop for that repository. A `default_branch_source` of `unknown` means the default branch could not be determined: say so and ask which it is before committing; under `ship`, that is a question the run cannot settle, so stop and report it.

## The message

A conventional commit, `{type}({scope}): {subject}`, with an optional body, ending in the footer when there is one. Every message holds to these:

- **The type follows the ticket's type**: `feat` for a `user-story` or `task`, `fix` for a `bug`, `chore` for `tech-debt` or a `spike`. Without a ticket, the diff decides it: `feat` for new behaviour, `fix` for a correction, `refactor` for a change that keeps behaviour, `chore` for the rest. A change set that is only documentation is `docs`; only tests, `test`.
- **The scope** is the project the change set touches, as a short noun, or the scope the repository's recent `git log` uses for it. None when the changes span projects with no common name.
- **The subject** is imperative, lowercase and without a trailing period, and the whole first line is at most 72 characters. A body of a few lines says what changed and why when the subject cannot carry it.
- **The footer links the ticket in its platform's form**: `Refs #{id}` for a GitHub ticket in the same repository, `Refs {owner}/{repository}#{id}` for one in another, `AB#{id}` for Azure DevOps, and none for a local ticket or without a ticket.
- **The footer is the last line.** No co-author trailer naming Claude or any AI, whatever the session's own commit guidance says.

## Commit

1. Outside `ship`, show each repository's file list and the message exactly as it will be committed, and wait for a yes. A change to either needs a new showing and a new yes. Under `ship`, commit.
2. Stage the change set by path, and commit only those paths, so whatever else the index holds stays staged and uncommitted: `git add -- <paths>`, then `git commit -F <message file> -- <paths>`, the message file in the system temp directory and deleted afterwards.
3. A hook that fails stops the commit: report its output. Nothing was committed, so after a fix the commit is attempted anew.

## Push

Only under `push` or `ship`, and only once `guard check --op push` allowed it: `git push`, or `git push -u origin <branch>` when the branch has no upstream. A branch with no remote has nowhere to go: say so.

After pushing, with a ticket, run `sync <reference>` once (with `--context`) and report it as `${CLAUDE_PLUGIN_ROOT}/shared/sync.md` says, so the pull request record sees the new commits' checks. Without a ticket there is nothing to sync.

## Report

Per repository: the commit's short SHA and subject, whether it was pushed and where, and every file left out (outside the change set, or refused as a secret).

## Invariants

- The guard is asked before every commit and push, and its refusal is final: no other way to the same write is looked for.
- Commits only the change set; never `git add -A`, never a refused file.
- Every run makes new commits: never `--amend`, never `--no-verify` or another hook skip, never a force-push.
- Outside a ship run, nothing is committed before an explicit yes to the exact message, and nothing is pushed unless `push` was given.
