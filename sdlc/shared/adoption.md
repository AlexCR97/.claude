# Adoption

Taking in a **non-ticket input**: something that is not a ticket reference but that a skill can still work on. `intake` owns the procedure; `plan`, `implement`, `checkpoint` and `resume` run it as their first step when they are given one, then carry on with the new ticket.

## What counts as a non-ticket input

- A path to an existing file (a spec, a markdown note).
- Pasted text or an idea, when the argument is not a path and does not resolve as a reference.
- No argument at all, when the skill needs a ticket and none is named: the current branch's work.

A reference that `resolve` finds is a ticket, never an input to adopt. Never use a branch name to guess an existing ticket; the current branch only supplies a title.

## Procedure

1. Read the input. For a file, the title is its first `#` heading, else its file name; for text, a short title you write; for a branch, the branch name with its prefix and ids stripped. For a branch, ask what the work is, since the branch holds no description.
2. Run `resolve --new --title "<title>"`. It creates nothing and reports where the ticket would live; a non-zero exit means the title cannot be filed, so stop and say so.
3. Decide the `type`: `user-story`, `task`, `bug`, `spike` or `tech-debt`. Say so. Default to `task` when unclear.
4. Ask **once**, showing the `ref`, the `type`, the directory and where the content comes from. Nothing is written before the yes; the user may change the title or the type in that same answer. Under the [ship flag](conventions.md#ship-runs), show the same and go on without asking.
5. Write the ticket (`ticket_json`, `ticket_file`) at the reported paths:
   - `ticket_file` holds a **copy** of the content under `# <title>`, in the sections a local ticket uses: `## Description` and `## Acceptance Criteria`. Put the input's text where it belongs; keep what the input states; where it states no acceptance criteria write `TODO`, never invent one.
   - `ticket_json`: `{"source": "local", "id", "title", "type", "url": null}`, plus `"origin": "<original path>"` for a file input (absolute path). Text and a branch have no origin.

## Invariants

- One confirmation, before anything is written, and none under the ship flag; nothing is created on a no.
- A copy, never a link: the new ticket's file is the single source of truth. A local ticket has no mirror, and `origin` is traceability only, never refreshed or read back.
- Never overwrite: an existing ticket is a different title, not a merge.
- The model decides the type and states it; the user can override it.
