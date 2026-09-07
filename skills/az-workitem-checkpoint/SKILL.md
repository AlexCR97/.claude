---
name: az-workitem-checkpoint
description: Records the current session's state on a work item as an entry in journal.md — where the code is, what was done, what was decided and why, what is blocking, and the single next action. Run it before switching away from a work item so a later /az-workitem-resume can pick the work up. Makes NO code changes.
---

## Purpose

`plan.md` records what the work *is*. It cannot record what a session *learned*, e.g. that one of two approaches was chosen and why, that a step turned out to be shaped differently than planned, that the branch is three commits in with an uncommitted edit that half-finishes Step X.Y. That context lives only in the conversation, and it dies with the session.

This skill writes it down. One entry per session, appended to `~/.az-workitems/{id}/journal.md`, so a new session later can read the top of one file and know where to start.

**It is the only skill that writes `journal.md`**, and `az-workitem-resume` is the only one that reads it. No other `az-workitem-*` skill touches the file: they work from `plan.md` and from what is already in the conversation, which keeps the journal out of their context entirely. The consequence is that this skill has to run — an unrecorded session leaves nothing behind but its step statuses.

So run it whenever attention leaves a work item: end of day, an interrupt, a context switch to something unrelated. It is cheap, and it is the last chance to keep what the session learned.

**Makes no code changes.** It writes exactly one file: `journal.md`.

---

## Paths

All `az-workitem-*` data lives under the current user's home directory, so the paths below are the same no matter which workspace the session runs in:

```
~/.az-workitems/
```

`~` is written for brevity. Neither the file tools nor a quoted shell argument expand it, so **resolve it to an absolute path before use** — `C:\Users\{user}` on Windows, `/home/{user}` on Linux, `/Users/{user}` on macOS.

```
~/.az-workitems/{id}/
├── digest.md              ← az-workitem-digest
├── journal.md             ← this skill only; read by az-workitem-resume
├── plan.md                ← az-workitem-plan
├── raw/                   ← az-workitem-fetch
└── artifacts/             ← az-workitem-plan and az-workitem-implement
```

---

## Input

```
/az-workitem-checkpoint [{id}] [{note}]
```

- `{id}` — the work item ID. When omitted, resolve it as described in step 1.
- `{note}` — optional free text the user wants recorded (e.g. `"stopping to review the PR for 18201"`). Fold it into the entry; never let it replace the entry's own content.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the work item ID

Take the first of these that yields an ID:

1. The ID passed with the invocation, or stated in the message.
2. The ID this session has been working on — a `/az-workitem-implement` or `/az-workitem-resume` run earlier in the conversation, or a `plan.md` already read.
3. The current git branch. Run the shared collector (see [step 2](#2-collect-the-git-state)) and read `work_item_ids_in_branch`. If it holds exactly one ID **and** `~/.az-workitems/{that id}/` exists, use it and say so:

   > Checkpointing #{id}, inferred from branch `{branch}`.

4. Otherwise, list the directories under `~/.az-workitems/` with their `journal.md` and `plan.md` modification times, newest first, and ask which one to checkpoint.

If `~/.az-workitems/{id}/` does not exist, stop:

> No local data for work item #{id}. Run `/az-workitem-fetch {id}` first.

### 2. Collect the git state

Locate the shared collector relative to this skill file — it lives in the sibling `az-workitem-common` directory, alongside `ado_auth.py`:

```
skills/az-workitem-common/collect-git-state.py
```

Run it from the repository the work is being done in:

```bash
python "{path-to-az-workitem-common}/collect-git-state.py"
```

It reports the repo name and root, the branch, HEAD, the base branch and merge base, commits ahead of base, commits the base has gained since, the working-tree counts, and any stashes. It writes nothing.

If `is_repo` is `false`, record `**Where:** not in a git repository` and carry on — an entry without git coordinates is still worth far more than no entry.

### 3. Reconstruct what this session did

This is the step that carries the skill. Everything else on disk is already recoverable; this is not.

Work back through the conversation and collect:

- **Done** — what actually changed: files created or edited, behavior that now works. Describe outcomes, not attempts. Where a change is not yet committed, say so.
- **Decisions** — every choice made in dialogue, with its *why* and what it was chosen over. A decision whose rationale is missing will be re-litigated in the next session, which is the exact cost this skill exists to avoid.
- **Inferences** — anything implemented on an assumption because the plan was underspecified, and the basis for it.

`az-workitem-implement` ends each run by reporting its decisions and inferences in chat precisely so that this step can find them. Where such a report is in this conversation, carry both lists over **verbatim** rather than paraphrasing them — that report is the only record of them, since implement does not write to this file.

Continue collecting:
- **Open questions** — what is unresolved, and who or what can resolve it.
- **Blockers** — what is preventing progress, and what would clear it.
- **Stopped at** — the step in flight and its honest state: what works, what does not, what is half-done. A step that is 80% finished must not read as complete.

Cross-check against `plan.md`: name the phase and step each item belongs to, so a later reader can jump straight to it. If the session's work has left a step's `**Status:**` line wrong, note it in step 6.

### 4. Establish the next action

The `**Next:**` line is the highest-value line in the entry, and the one a resume reads first. It must be specific enough to act on without re-reading the plan — a file and an action, not a phase name.

Good:

> **Next:** Fix the DI registration for `IUserAuthorizationReader` in `BenchmarkSetup.cs:41`, then run Step 2.7's harness and capture the output.

Not good:

> **Next:** Continue Phase 2.

Derive it from the session where the session makes it obvious. Where it does not — the session ended on an open question, or several things could reasonably come next — **ask the user** rather than guessing:

> What is the next action on #{id}? I have it as "{best inference}" — correct it or confirm.

Wait for the answer. A wrong `**Next:**` line is worse than an absent one, because it will be trusted.

When nothing is pending — every phase done — write that plainly: `**Next:** Nothing pending; all phases complete. Awaiting review.`

### 5. Write the entry

Read the template at `skills/az-workitem-checkpoint/journal-template.md` and follow its structure.

**If `journal.md` does not exist**, create it with the header from the template — the title line (linking the ADO work item, whose URL follows `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`, reading `org` and `project` from `~/.az-workitems/config.json`) and the note about entry ordering — then write this entry as the first one.

**If it exists**, insert the new entry **immediately after the header block, above the existing newest entry**, separated by `---`. Entries run newest first so the current state is the top of the file rather than the end of a growing scroll.

Rules for an entry:

- Timestamp the heading in **UTC**, matching the `> Generated on` convention in `digest.md` and `plan.md`.
- Name the phase and step the session was in, so the heading alone locates the work.
- `**Where:**`, `**Working tree:**`, `**Stopped at:**` and `**Next:**` are always present. Where a fact is unavailable, say so explicitly rather than omitting the line.
- Omit any of the `### Done`, `### Decisions`, `### Inferences`, `### Open questions` and `### Blockers` sections that would be empty. Do not pad an entry with a heading over nothing.
- **Never edit or delete an existing entry.** A session's account of itself is not regenerable — the one thing here that no later run can reconstruct. A correction is a new entry saying what it corrects.
- Keep it factual and short. An entry is read in a hurry, by someone who has forgotten everything.

### 6. Reconcile plan.md status lines

If the session left a step's status stale, correct only the `**Status:**` lines and the affected Progress table rows in `plan.md` — nothing else:

- A step that was started and is not finished → `In Progress`, with a note saying what remains
- A step that cannot proceed → `Blocked`, with a note saying what is blocking
- A step finished this session → `Done`

Use the vocabulary and note rules defined in `skills/az-workitem-plan/SKILL.md`. Then recompute the phase's Progress table row from its steps.

If no status line needs changing, leave `plan.md` untouched.

### 7. Report

Confirm in **two lines at most**. Do not print the entry body in chat — it was just written to a file the user can open.

> Checkpointed #{id} to `~/.az-workitems/{id}/journal.md` — {phase/step}, next: {the Next line, condensed}.
> {Updated Step {N}.{M} to {status} in plan.md. | plan.md unchanged.}

---

## Constraints

- **Never create, edit, or delete any source code file** — this skill only records state
- Write only `journal.md`, plus `**Status:**` lines and Progress table rows in `plan.md` when step 6 applies. Never touch `digest.md`, `raw/`, or anything under `artifacts/`
- Never edit or delete an existing journal entry — append a correcting entry instead
- Run only read-only commands. `collect-git-state.py` is read-only; do not run `git fetch`, `git pull`, `git add`, `git stash`, or any other command that changes repository state
- Never run a git operation that writes — the developer decides when to commit, stash or push
- Never invent a `**Next:**` line — derive it from the session, or ask
- Never record a decision without its rationale; the *why* is the reason the entry exists
- Do not print the entry body in chat — the report is two lines
- Do not re-fetch the work item or check ADO — this skill records local state; `/az-workitem-resume` is what checks ADO for drift
