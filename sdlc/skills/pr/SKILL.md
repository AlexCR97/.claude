---
name: pr
description: Opens a draft pull request for a ticket branch, or marks it ready for review, and records it in the ticket's pull request record. Use when asked to open, update or ready a pull request for sdlc ticket work.
argument-hint: "[<ticket reference>] [ready] [ship] [note]"
---

# Pull request

Open the pull request that delivers the ticket `$ARGUMENTS` names, or mark it ready, through the best-suited installed skill or the procedure below, then record it. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The pull request record follows `${CLAUDE_PLUGIN_ROOT}/shared/journal.md`, the guard `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`, and each host's commands are under "Pull requests (for `pr`)" in `${CLAUDE_PLUGIN_ROOT}/shared/providers/github.md` and `${CLAUDE_PLUGIN_ROOT}/shared/providers/ado.md`. Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The ticket**: a reference, resolved with `resolve <reference>` (add `--context {namespace}[/{product}]` when the session has one). No reference: the ticket this session has been working on, else ask. Never infer the ticket from the branch name.
- **`ready`**: the literal word. Marks the pull request ready for review, opening it first when there is none. Without it, a new pull request is a draft and an existing one keeps its state.
- **`ship`**: the [ship flag](../../shared/conventions.md#ship-runs). It waives this skill's confirmations; nothing this skill does is a hard stop.
- **A note**: trailing free text for the body, such as the failure a ship run stopped at.

## Where

One pull request per repository the work changed: each worktree in the plan's Workspace whose branch has commits ahead of its target, or the invocation directory's worktree when there is no plan.

- **Head**: the worktree's branch. A protected one (`guard protected --repo <worktree>`, with `--context`) is refused: work reaches a protected branch only through a ticket branch.
- **Target**: the branch the ticket branch was cut from, the remote's default branch, unless the user names another.
- **Host**: read from `git -C <worktree> remote get-url origin`: GitHub or Azure Repos, whatever the ticket's source. Another host, or no remote: say so and stop for that worktree.

## Choose who opens it

A delegate or the built-in below, chosen as [Delegates](../../shared/conventions.md#delegates) says. A delegate fits when it opens pull requests on this host and suits the situation better than the built-in: one that carries the namespace's conventions (an employer's plugin on that employer's repositories), or a project skill of the repository. Its job is the pull request alone: creating or updating it and marking it ready. A skill that also merges, or asks how to integrate, does not fit; one that only writes a body is a template the built-in may follow for its summary.

- **A delegate**: invoke it with the Skill tool, passing `ready` when given. Under ship, also pass every argument it would otherwise infer and confirm. Then read the body the delegate left: when it lacks the ticket link or, under ship, the decisions (both as in Body), add them with the host's body update; without ship, show the addition and ask first. Then Record.
- **No suitable delegate**: the built-in below, then Record.

## Built-in

1. **Pushed at its tip.** `git fetch origin {branch}`, then compare `git rev-parse HEAD` with `origin/{branch}`. A branch missing on the remote, or a remote tip that differs from the local one, is refused: say which, and that the branch must be pushed first (`/sdlc:commit` pushes under ship). This skill never pushes. Uncommitted changes are not in the pull request: name them in the report.
2. **Something to deliver.** No commits ahead of `origin/{target}`, or an empty `git diff origin/{target}...origin/{branch}`: say so and stop.
3. **Find the existing pull request** whose head is the branch, open or draft, with the host's list command. There is one: this run updates it. Several: ask which; under ship, that is a question the run cannot settle, so stop and report it for this repository.
4. **Write the title and body.** The title is a conventional subject, typed as `/sdlc:commit` types a commit message, summing up the net change in at most 72 characters. The body is in Body.
5. **Confirm.** Without ship, show the host, repository, head, target, title, the whole body, and whether the result is a draft or ready, and ask for a yes. Anything else is a no: write nothing. Under ship, go on.
6. **Write.** No pull request: create it as a draft. One exists: replace its title and body. Then, with `ready`, mark it ready: it only ever moves forward, never back to draft. A failed command: report it and the state it left (created but still a draft, a body updated), and go on to Record with what exists.

## Body

```markdown
{the note, when there is one}

{one or two sentences: what the change does and why}

## Changes

- {one logical change, in the imperative, naming files, types or endpoints inline}

## Decisions

- **{decision}** - {why, what it was chosen over, and its cost if wrong, as the journal entry words it}

{ticket link}
```

- **Changes describe the net change**, `git diff origin/{target}...origin/{branch}`: one bullet per change a reviewer reviews as one, the change the others build on first. Commit messages say why; the diff says what landed. Rewrite the body from the current net change on every run.
- **Decisions, under ship only**: every decision a ship run made on this ticket, so a resumed run keeps the first run's: the `### Decisions` of each journal entry marked as a ship run's (`journal.md`), oldest first, each decision once and verbatim, then any the run has stated since its latest entry. With none, write `None.` Without ship, omit the section.
- **The ticket link** in the host's own form, so the host links it:

  | Ticket source | GitHub host                                                                 | Azure Repos host                            |
  | ------------- | --------------------------------------------------------------------------- | ------------------------------------------- |
  | GitHub        | `Closes #{n}`, or `Closes {owner}/{repository}#{n}` from another repository | the issue's URL                             |
  | Azure DevOps  | `AB#{id}`, bare                                                             | `#{id}`                                     |
  | Local         | none: the body stands alone                                                 | none                                        |

- **The body is the only link.** Nothing is written onto the ticket itself, such as an Azure DevOps work item link, since this skill never changes the ticket.
- **Never restate the ticket**: its description and acceptance criteria live upstream, and the link is their source of truth.

## Record

Rewrite `pulls.md` in the ticket directory as `journal.md` "Pull request record" says, with every pull request this run opened or updated among its lines: refresh the status of each line with the host's view command, together, under one time. A failed refresh keeps the previous statuses and adds its `Refresh failed` line. This is local: nothing goes upstream.

## Report

Per pull request: created or updated, draft or ready (and that `ready` moved it), who opened it (the delegate's name, or the built-in), title, target, URL, and any uncommitted changes left out. Then the number of pull requests in `pulls.md`.

## Invariants

- Writes upstream only the pull request itself: create, title, body, draft to ready. Never merges, closes, approves or retargets one, never comments on or changes the ticket, and never pushes, commits or edits the branch.
- Without ship, nothing goes upstream before an explicit yes to exactly what will be written: the built-in's, or a delegate's own confirmation. Under ship, nothing waits: opening and readying a pull request are not hard stops.
- Locally, writes only `pulls.md`. Scratch files (a body, a JSON payload) go in the system temp directory and are deleted afterwards.
- Every value comes from git, the host, the ticket directory or the user; nothing in the body is invented.
- Never a co-author trailer or a tooling footer in the body.
- Never read, print or store a token; `gh` and `az` hold the sign-in.
