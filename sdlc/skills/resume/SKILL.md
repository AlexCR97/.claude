---
name: resume
description: Rebuilds a ticket's context in a fresh session and prints one briefing that ends in the single next action, covering what the work is, where it stopped, the live state of the code and what changed upstream since the ticket was last mirrored. Read-only.
disable-model-invocation: true
argument-hint: "[<ticket reference>]"
---

# Resume

Brief a fresh session on the ticket `$ARGUMENTS` names. Everything needed is on disk, but two things no file holds have usually moved: the code and the ticket. Read it all back and print one briefing. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The journal is `${CLAUDE_PLUGIN_ROOT}/shared/journal.md`, the plan `${CLAUDE_PLUGIN_ROOT}/shared/plan.md`, the artifacts `${CLAUDE_PLUGIN_ROOT}/shared/artifacts.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- A ticket reference. Run `resolve <reference>`, adding `--context {namespace}[/{product}]` when the session has a context.
- No reference: the ticket this session has been working on. Failing that, list the tickets in the SDLC home (`{namespace}/{product}/{source}/{id}`), the session context's product first, each with its title and the date of its latest journal entry, and ask which. Never infer the ticket from the branch name: a wrong guess briefs the session on the wrong work.
- A non-ticket input (a file, text or an idea) has nothing to resume. Say so and offer adoption by `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md`, which asks once; the briefing then covers the new ticket, whose plan and journal do not exist yet.

## Reads

1. **The ticket**, from the ticket directory `resolve` reports: `raw/ticket.md` for a local ticket, else the mirror `raw/raw.json` (GitHub: `issue`, `comments`, `parent`, `blocked_by`; Azure DevOps: `work_item`, `comments`, `relations`). Two or three sentences: the goal and what done looks like. Not a dump.
2. **The plan**, if there is one: the Progress table, the Workspace, and each step that is `In Progress` or `Blocked`, then the first `Pending` one. Report a stale-looking status; never correct it.
3. **The latest journal entry only**: the last file in `journal/` by name, read in full. It stands alone, so never read an older one, not even to look something up. No journal: say so, reconstruct where the work stopped from the plan and the code, label it a reconstruction, and recommend `/sdlc:checkpoint`.
4. **The code**: in each worktree of the plan's Workspace, git reads only (branch, HEAD, uncommitted and untracked files, stashes, commits ahead of the base branch). Compare the invocation directory and the entry's **Where** with the Workspace and say plainly when they differ: every plan target is relative to a worktree. The base branch's movement is as of the last fetch; this skill does not fetch.
5. **Artifacts** the plan cites for the in-flight or next step, and `planning/`: their `README.md` files. Never run a script under `artifacts/`, even a read-only one.
6. **Pull requests**, from `pulls.md` if present, with the time of its statuses.
7. **Upstream**, for a remote ticket: `fetch <reference> --check`, with `--context` as above. It writes nothing and compares revisions, not content.
   - `unchanged`: one line.
   - `changed`: read the live ticket with `gh api` or `az rest` (reads only) and say what kind of change it is, comparing with the mirror: title, state, labels or tags, description, new comments (author, age, a snippet), relations. A new comment answering an open question of the journal is the most valuable finding. Suggest `/sdlc:intake <reference>` to refresh before continuing; this skill never refreshes.
   - `never_mirrored`: say so. `local`: nothing upstream. An error: report it in one line; a failed check never blocks the briefing.

## The briefing

One message, sections in this order, any with nothing to say omitted: the ticket (reference, title, type, state, product), **The work**, **Where it stopped** (the entry's Stopped at, verbatim), **Progress**, **Code**, **Pull requests**, **Carried forward** (open decisions, questions and blockers of the entry), **Changed upstream**, and last **Next**, the entry's Next line verbatim. Without a journal, Next is the plan's first `In Progress`, `Blocked` or `Pending` step, labelled as inferred; without a plan, `/sdlc:plan <reference>`. Exactly one next action closes the briefing.

When the session has no context, adopt the ticket's namespace and product for the session: open the briefing with `Session context: {namespace}/{product} (adopted from {reference})` and pass `--context` on every later call. This lives in the conversation only. A context that is set is never replaced; where the ticket is outside it, say so.

## Invariants

- Writes nothing: no code, no entry, no plan, no mirror, no `ticket.json`. The one exception is an adoption the user confirmed. Starts nothing: no plan, no implementation, no refresh.
- Git, `gh` and `az` are used to read. Never commit, stash, fetch, check out or push.
- Label every reconstruction; never present an inference as a record.
- The ticket's content comes from the mirror or `raw/ticket.md`, never from a derived summary.
