---
name: pr
description: Opens a draft pull request for a branch's work, or marks it ready for review, with a body that links the sdlc ticket when there is one, and records it in the ticket's pull request record. Use when asked to open, update or ready a pull request for sdlc ticket work, or to open one with sdlc.
argument-hint: "[<ticket reference>] [ready] [ship] [note]"
---

# Pull request

Open the pull request that delivers the work `$ARGUMENTS` points to, with or without an sdlc ticket, or mark it ready, always by the procedure below, then record it. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). Sync follows `${CLAUDE_PLUGIN_ROOT}/shared/sync.md`, the journal and the pull request record `${CLAUDE_PLUGIN_ROOT}/shared/journal.md`, the guard `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`, and each host's commands are under "Pull requests (for `pr`)" in `${CLAUDE_PLUGIN_ROOT}/shared/providers/github.md` and `${CLAUDE_PLUGIN_ROOT}/shared/providers/ado.md`. Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The ticket**, optional: a reference, resolved with `resolve <reference>` (adding `--context {namespace}[/{product}]` when the session has one). No reference: the ticket this session has been working on, else ask once, with "no ticket" as an option. Never infer the ticket from the branch name. With a ticket, read its `source`, `id`, `type` and `coordinates` from `ticket.json`, and its `plan.md` when there is one.
- **`ready`**: the literal word. Marks the pull request ready for review, opening it first when there is none. Without it, a new pull request is a draft and an existing one keeps its state.
- **`ship`**: the [ship flag](../../shared/conventions.md#ship-runs). It waives this skill's confirmations; nothing this skill does is a hard stop.
- **A note**: trailing free text for the body, such as the failure a ship run stopped at.

## Where

One pull request per repository the work changed: each worktree in the plan's Workspace whose branch has commits ahead of its target, or the invocation directory's worktree when there is no plan.

- **Head**: the worktree's branch. A protected one (`guard protected --repo <worktree>`, with `--context`) is refused: work reaches a protected branch only through a ticket branch.
- **Target**: the branch the head was cut from, the remote's default branch, unless the user names another.
- **Host**: read from `git -C <worktree> remote get-url origin`: GitHub or Azure Repos, whatever the ticket's source. Another host, or no remote: say so and stop for that worktree.

## Procedure

1. **Sync**, with a ticket: `sync <reference>` (with `--context`), reported as `sync.md` says. Without a ticket there is nothing to sync.
2. **Pushed at its tip.** `git fetch origin {branch}`, then compare `git rev-parse HEAD` with `origin/{branch}`. A branch missing on the remote, or a remote tip that differs from the local one, is refused: say which, and that the branch must be pushed first (`/sdlc:commit` pushes under ship). This skill never pushes. Uncommitted changes are not in the pull request: name them in the report.
3. **Something to deliver.** No commits ahead of `origin/{target}`, or an empty `git diff origin/{target}...origin/{branch}`: say so and stop.
4. **Find the existing pull request** whose head is the branch, open or draft, with the host's list command. There is one: this run updates it. Several: ask which; under ship, that is a question the run cannot settle, so stop and report it for this repository.
5. **Write the title and body.** The title is a conventional subject, typed as `/sdlc:commit` types a commit message, summing up the net change in at most 72 characters. The body is in Body.
6. **Confirm.** Without ship, show the host, repository, head, target, title, the whole body, whether it fills the repository's template, and whether the result is a draft or ready, and ask for a yes. Anything else is a no: write nothing. Under ship, go on.
7. **Write.** No pull request: create it as a draft, with the ticket's link as the host's create command takes it. One exists: replace its title and body. Then, with `ready`, mark it ready: it only ever moves forward, never back to draft. A failed command: report it and the state it left (created but still a draft, a body updated), and go on to Record with what exists.

## Body

The repository's own template when it has one at the host's standard location, at the root of the target branch (`git show origin/{target}:{path}`, the file name in any letter case): `.github/pull_request_template.md` on GitHub, `.azuredevops/pull_request_template.md` on Azure Repos. Otherwise this template:

```markdown
{the note, when there is one}

## Summary

{one sentence: what the change does and why}

{the ticket link}

## Root cause

- {the mechanism that produced the bug}

## Pre-merge

- {what whoever reviews or merges must act on or weigh}

## Post-merge

- {what must happen once it lands}

## Changes

- {one logical change, in the imperative, naming files, types or endpoints inline}
- Mechanical: {renames, formatting, generated files, lockfiles}

## Evidence

- `{command}`: {its result}
- Not verified: {what nothing ran against}

## Decisions

- **{decision}** - {why, what it was chosen over, and its cost if wrong, as the journal entry words it}

{n} process decisions are in the ticket's journal.
```

- **Omit every section with nothing in it**, heading included. Plain bullets throughout, never checkboxes: the body is rewritten on every run.
- **Summary** is one sentence, what the change does and why, then the ticket link on its own line.
- **Root cause**, for a `bug` ticket only: the mechanism that produced the symptom, as the work established it.
- **Pre-merge** is what whoever reviews or merges must act on or weigh: a migration, a config step, a breaking change, a one-way door, a merge order with another pull request, a path left untested. Under ship, a ticket whose description or acceptance criteria changed while the run kept its plan, as `sync.md` says, gets a line naming the fields: from this run's sync, from an inference the run stated earlier, or from an `(assumed)` decision in an entry marked as a ship run's. Each line names a concrete action or risk; a line that only reassures is left out.
- **Post-merge** is what must happen once it lands: a deployment, a migration or config step per environment, advancing the ticket's state where the merge does not, a follow-up split off from this work.
- **Changes describe the net change**, `git diff origin/{target}...origin/{branch}`: one bullet per change a reviewer reviews as one, in review order, the change the others build on first. A closing `Mechanical:` bullet gathers the changes a reviewer only skims. Commit messages say why; the diff says what landed. Rewrite them from the current net change on every run.
- **Evidence** lists each command run on the change, by this session or as a ship run's journal records it, with its result; then what nothing verified.
- **Decisions, under ship only**: the decisions about the code a ship run made on this ticket, so a resumed run keeps the first run's. Read the `### Decisions` of each journal entry marked as a ship run's (`journal.md`), oldest first, then any the run has stated since its latest entry, and list once and verbatim each decision about what the change does or how it behaves: its design, an assumption about the data, a test seam, a case left out. A process decision (the workspace, the worktree, the branch, tooling, the order of work, a probe skipped) stays in the journal only. End the section with `{n} process decisions are in the ticket's journal.` when there are any. With no decision about the code, write `None.` before that line.
- **Never restate the ticket**: its description and acceptance criteria live upstream, and the link is their source of truth.

**Filling the repository's template**: keep its headings, their order and its checklists, and put under each what the section above of the same purpose holds, by the same rules; drop its instruction comments (`<!-- ... -->`). Under a heading nothing fills, write `None.` Tick a checklist item only when the evidence shows it holds, and keep every item ticked in the body being replaced. The note goes first. The ticket link goes where the template asks for linked issues or work items, and under ship the Decisions and the changed-ticket line where it asks for decisions or pre-merge notes; what it has no place for is appended, as the sections above, with the ticket link last.

**The ticket link** is in the host's own form, so the host shows it on the pull request and the ticket:

| Ticket source  | GitHub host                                                                 | Azure Repos host                                                      |
| -------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| GitHub         | `Closes #{n}`, or `Closes {owner}/{repository}#{n}` from another repository | the issue's URL                                                       |
| Azure DevOps   | `AB#{id}`, bare                                                             | `#{id}`, plus `workItemRefs` at creation (`ado.md` says when it fits) |
| Local, or none | none: the body stands alone                                                 | none                                                                  |

A `Closes` link on GitHub takes only when the target is the default branch (`github.md`); against another target the report says so.

## Record

With a ticket, run `sync <reference>` (with `--context`), adding `--pull <url>` for every pull request this run opened or updated, and report it as `sync.md` says: it adds them to `pulls.md` and refreshes every line under one time. This is local: nothing goes upstream. Without a ticket there is no record.

## Report

Per pull request: created or updated, draft or ready (and that `ready` moved it), title, target, URL, whether it filled the repository's template, the ticket link (and when a `Closes` link does not take, because the target is not the default branch), and any uncommitted changes left out. Then, with a ticket, the number of pull requests in `pulls.md`.

## Invariants

- Writes upstream only the pull request itself: create, title, body, draft to ready. Never merges, closes, approves or retargets one, and never pushes, commits or edits the branch.
- Never changes the ticket beyond adding the pull request link: the link in the body and, on Azure Repos, `workItemRefs` at creation. No comment, field, state or other relation.
- Without ship, nothing goes upstream before an explicit yes to exactly what will be written. Under ship, nothing waits: opening and readying a pull request are not hard stops.
- Locally, writes only what `sync` writes (the mirror and `pulls.md`). Scratch files (a body, a JSON payload) go in the system temp directory and are deleted afterwards.
- Every value comes from git, the host, the ticket directory, the session or the user; nothing in the body is invented.
- Never a co-author trailer or a tooling footer in the body.
- Never read, print or store a token; `gh` and `az` hold the sign-in.
