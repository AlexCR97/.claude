---
name: checkpoint
description: Records the session on an sdlc ticket as a journal entry (where the code is, what was done and decided, what blocks, the next action), posts it on a remote ticket, and refreshes the plan's step statuses and the pull request record. Use when asked to checkpoint an sdlc ticket or record its progress in the journal.
argument-hint: "[<ticket reference | spec file | text or idea>] [ship] [note]"
---

# Checkpoint

Record this session on the ticket `$ARGUMENTS` names, so a later `resume` can pick the work up, on this machine or, for a remote ticket, on any other. The plan says what the work is; what a session learned dies with it unless this writes it down. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The entry follows `${CLAUDE_PLUGIN_ROOT}/shared/journal.md`, the sync `${CLAUDE_PLUGIN_ROOT}/shared/sync.md`, the statuses `${CLAUDE_PLUGIN_ROOT}/shared/plan.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- A ticket reference, or a non-ticket input (a spec file, text or an idea) that is adopted first. Trailing free text is a note to fold into the entry, never a replacement for its content.
- No reference: the ticket this session has been working on. Failing that, ask: list the tickets in the SDLC home (the session context's product first, each with its title and latest journal entry) and ask which. Never infer the ticket from the branch name: a wrong guess attaches a session's account to the wrong ticket, and nothing can regenerate it.
- `ship`: the [ship flag](../../shared/conventions.md#ship-runs), never part of the reference or the note. Under it this skill asks nothing, and the ship run always names its ticket.

## Steps

1. **Resolve.** Run `resolve <reference>`, adding `--context {namespace}[/{product}]` when the session has a context. A non-ticket input is adopted by `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md` (one confirmation, none under `ship`) and the new ticket is checkpointed. A ticket outside the session context: ask before going on, naming its product and the context, defaulting to no; under `ship`, name both and go on, since the run named the ticket.
2. **Sync.** Run `sync <reference>` (with `--context`), adding `--pull <url>` for each pull request the session opened or named as delivering this ticket, and report it as `${CLAUDE_PLUGIN_ROOT}/shared/sync.md` says. It records and refreshes the pull requests.
3. **Read the code's state with git reads** in each worktree the plan's Workspace lists, or the invocation directory when there is no plan: repository, worktree, branch, HEAD, base branch, uncommitted and untracked files, stashes. Read only.
4. **Reconstruct the session** from the conversation: its outcomes, every decision with its why and the alternative, every inference with its basis (an assumed decision), and where the step in flight honestly stands. Read the latest journal entry for what is still open. Under `ship`, each decision carries its cost if wrong (`journal.md`), and the decisions in the plan's Decisions section join the session's: carry each over in its own wording unless an entry marked as a ship run's already holds it, so every decision a ship run made reaches the journal once.
5. **Settle Next.** Derive it from the session. When several things could come next, give the best inference and ask the user to accept or correct it: a wrong Next is worse than none. Under `ship`, write the best inference without asking, and record it as an assumed decision that names the alternative.
6. **Write the entry** as a new file in the ticket directory's `journal/`, in the format and the budget of about 250 words of `journal.md`. Under `ship`, it has the Ship run line.
7. **Post upstream**, when the ticket's source declares `writes_comments` in `${CLAUDE_PLUGIN_ROOT}/shared/providers/{source}.json` (GitHub and Azure DevOps). A local ticket's journal stays on disk; skip to the next step. Post, oldest first, each entry `ticket.json` lists under `unposted_journal`, then the new one: one comment each, in the posted form and by the backlog rules of `journal.md`, with the commands of the source's provider note (`${CLAUDE_PLUGIN_ROOT}/shared/providers/{source}.md`, "Posting a journal entry"). Posting is always on; there is nothing to ask. At the first failed post, stop posting: list it and every entry after it in `unposted_journal`, oldest first, keep their files, and carry on with the checkpoint. Done when every entry has a comment or a place in `unposted_journal`.
8. **Reconcile `plan.md`.** Correct each step `**Status:**` the session left stale (`In Progress` or `Blocked` with their one-line note, or `Done`) and derive the affected Progress rows again. Change nothing else in the plan.
9. **Report in two lines**, without printing the entry: the ticket, the new file, the stage and the Next; then each status changed, or that the plan is unchanged, the number of pull requests recorded, and the number of entries posted. When a post failed, add a third line: the entries left unposted and the error; the next checkpoint posts them.

## Invariants

- Writes only a new journal entry, the `**Status:**` lines and Progress rows of `plan.md`, and `unposted_journal` in `ticket.json`, beyond what `sync` writes (the mirror and `pulls.md`). Never code, never `artifacts/`, never the rest of the plan.
- Git is used to read. `gh` and `az` are used to read and to post journal entries as comments on the ticket, and for nothing else upstream: the plan, the pull request record and artifacts stay local. Never commit, stash, push, fetch, check out, or open or change a pull request, an issue or a work item.
- Never edit or delete an existing entry or its comment; a correction is a new entry.
- Syncs once, at the start, never after posting: the next skill's sync sees the post as this machine's own.
- A pull request reaches the record through `sync`: from the branches the plan's Workspace lists, or by `--pull` from what the session says, never from a branch name that resembles the ticket. Where it is unclear which ticket one belongs to, ask before passing it; under `ship`, leave it out and say so in the entry.
- Never record where the ticket is filed.
