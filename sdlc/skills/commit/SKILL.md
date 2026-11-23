---
name: commit
description: Commits an sdlc ticket's phase or session changes with a conventional message that links the ticket, through a better-suited installed commit skill or its own procedure. Use when asked to commit work on an sdlc ticket, and when /sdlc:ship finishes a phase.
argument-hint: "[<ticket reference>] [<phase>] [push] [ship]"
---

# Commit

Commit the changes of the ticket `$ARGUMENTS` names: one commit per repository the changes span. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The protected-branch policy is `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The ticket**: a reference, resolved with `resolve <reference>` (adding `--context {namespace}[/{product}]` when the session has one). No reference: the ticket this session has been working on, else ask. Read its `source`, `id`, `type` and `coordinates` from `ticket.json`, and its `plan.md` when there is one.
- **The phase**, if named: its number in `plan.md`. Otherwise the changes are the session's.
- **`push`**: push the commit afterwards. Without it, and outside a ship run, the commit stays local.
- **`ship`**: a ship run invoked this skill, as [Ship runs](../../shared/conventions.md#ship-runs) says. Committing and pushing the ticket branch are not hard stops, so nothing here asks under it ([ADR 0008](../../docs/adr/0008-a-ship-run-may-commit-push-and-open-pull-requests.md)).

## 1. The changes

The **change set** is the files the phase or the session changed, in each worktree and plain directory the plan's Workspace lists (no plan: the invocation directory's repository). The phase's step targets and the edits this conversation made name them; `/sdlc:document` edits made for the same projects belong with them. Read `git status --porcelain` in each repository and match it against the change set:

- A changed file outside the change set stays out. Name it, so the user knows it was left.
- A file in the change set that git shows unchanged has nothing to commit.
- Nothing left in any repository: say so and stop.

**Secret-looking files are refused.** A path such as `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `credentials.*`, `secrets.*`, or any name holding `secret` or `password`, and any file whose diff adds what looks like a private key, token or password, leaves the change set. A template holding no values, such as `.env.example`, is not one. Name each refused file and why; the user commits a false positive by hand.

## 2. The guard

For each repository with changes, ask `guard check --op commit --repo <worktree directory>`, with `--context` when the session has one. A refusal is final: report its `reason` and stop for that repository. A `default_branch_source` of `unknown` means the default branch could not be determined: say so and ask which it is before committing.

## 3. Who commits

Choose by judgement, each run, between an installed delegate and the built-in procedure below. No config names a delegate.

- **A delegate fits** when it carries conventions this work must follow, such as the commit skill of the plugin that owns the namespace's repositories (an employer's, for the employer's repositories), and when it can be held to the change set: one that stages the whole tree fits only when the tree holds nothing outside the change set.
- **A delegate does not fit** when it commits without showing the message and this is not a ship run (the user's yes would be lost), or when it would add a co-author trailer.
- Say the choice in one line before acting: the delegate and why it fits, or that the built-in runs because none does.

**Running a delegate.** Invoke it with the Skill tool. Before invoking it, state the commit type and the ticket footer of step 4, so the message it crafts carries them. Its own gates run. Under `ship`, pass its own approval flag (such as `approve`); pass its push flag (such as `push`) only under `push` or `ship`, once `guard check --op push` allowed it. A delegate that only the user can invoke is handed to the user to type, with the arguments to give it. The guard and the refusals of step 1 hold whichever commits.

## 4. The message (built-in)

A conventional commit: `{type}({scope}): {subject}`, an optional body, then the footer.

- **Type** from the ticket's type: `feat` for `user-story` and `task`, `fix` for `bug`, `chore` for `tech-debt` and `spike`. Where the change set is only documentation, `docs`; only tests, `test`.
- **Scope**: the project the change set touches, as a short noun, or the scope the repository's recent `git log` uses for it. Omit it when the changes span projects with no common name.
- **Subject**: imperative, lowercase, no trailing period, the whole first line at most 72 characters.
- **Body**: a few lines on what changed and why, when the subject cannot carry it.
- **Footer** links the ticket in its platform's form: `Refs #{id}` for a GitHub ticket in the same repository, `Refs {owner}/{repository}#{id}` for one in another; `AB#{id}` for Azure DevOps; none for a local ticket.
- The message ends with the footer: no co-author trailer, ever, whatever the session's own commit guidance says.

## 5. Commit (built-in)

1. Outside `ship`, show each repository's file list and the message exactly as it will be committed, and wait for a yes. A change to either needs a new showing and a new yes. Under `ship`, commit.
2. Stage the change set by path, and commit only those paths, so whatever else the index holds stays staged and uncommitted: `git add -- <paths>`, then `git commit -F <message file> -- <paths>`, the message file in the system temp directory and deleted afterwards.
3. A hook that fails stops the commit: report its output. Nothing was committed, so after a fix the commit is attempted anew.

## 6. Push

Only under `push` or `ship`, and only once `guard check --op push` allowed it: `git push`, or `git push -u origin <branch>` when the branch has no upstream. A branch with no remote has nowhere to go: say so.

## Report

Per repository: the commit's short SHA and subject, whether it was pushed and where, and every file left out (outside the change set, or refused as a secret). Name the delegate when one committed.

## Invariants

- The guard is asked before every commit and push, and its refusal is final: no other way to the same write is looked for.
- Commits only the change set; never `git add -A`, never a refused file.
- Every run makes new commits: never `--amend`, never `--no-verify` or another hook skip, never a force-push.
- No co-author trailer naming Claude or any AI, in the built-in's message or a delegate's.
- Outside a ship run, nothing is committed before an explicit yes to the exact message, and nothing is pushed unless `push` was given.
