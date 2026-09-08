---
name: az-workitem-resume
description: Rebuilds the context for a work item in a fresh session — reads journal.md, plan.md, digest.md and prior artifacts, inspects the live git state, and checks whether the ADO work item changed since it was last fetched. Outputs a briefing ending in the single next action. Read-only; makes NO changes.
argument-hint: "[id]"
---

## Purpose

A work item gets put down and picked up days later in a new session that knows nothing about it. Everything needed is already on disk — the digest, the plan, the artifacts, the journal — but reading it back into context by hand is slow and easy to do incompletely, and two things no file can hold have usually drifted in the meantime: the state of the working tree, and the work item itself.

This skill assembles all of it into one briefing: what the work is, where it stopped, what the next action is, what the code looks like right now, and what changed in ADO while attention was elsewhere.

**Read-only.** It writes nothing, changes no code, and starts no work — it ends by offering the next action, and waits.

---

## Paths

All `az-workitem-*` data lives under the current user's home directory, so the paths below are the same no matter which workspace the session runs in:

```
~/.az-workitems/
```

`~` is written for brevity. Neither the file tools nor a quoted shell argument expand it, so **resolve it to an absolute path before use** — `C:\Users\{user}` on Windows, `/home/{user}` on Linux, `/Users/{user}` on macOS.

```
~/.az-workitems/{id}/
├── digest.md              ← what the work item asks for
├── journal.md             ← what past sessions did, decided and left unfinished
├── plan.md                ← the phased plan and its per-step status
├── raw/                   ← the fetched ADO data
└── artifacts/             ← research, probes and captured measurements
```

---

## Input

```
/az-workitem-resume [{id}]
```

`{id}` — the work item ID. When omitted, resolve it as described in step 1.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the work item ID

Take the first of these that yields an ID:

1. The ID passed with the invocation, or stated in the message.
2. The current git branch. Run the collector from [step 4](#4-read-the-live-git-state) and read `work_item_ids_in_branch`. If it holds exactly one ID **and** `~/.az-workitems/{that id}/` exists, use it and say so:

   > Resuming #{id}, inferred from branch `{branch}`.

3. Otherwise, list every directory under `~/.az-workitems/` (ignoring `config.json`), each with its title from `digest.md`, the date of its newest `journal.md` entry, its phase progress from `plan.md`, and its newest modification time — most recently touched first. Ask which one to resume.

That listing is worth printing whenever the user does not name an ID, because "which work item was I in the middle of" is half the problem this skill solves.

If `~/.az-workitems/{id}/` does not exist, stop:

> No local data for work item #{id}. Run `/az-workitem-fetch {id}` to start.

### 2. Read what past sessions recorded

Read, in this order, and stop reading any file as soon as you have what the briefing needs:

**`journal.md`** — the newest entry in full, and enough of the two before it to see decisions and blockers that are still open. This is the primary source: it is the only file that records *why* things are the way they are. If it does not exist, note that and continue — step 3 reconstructs what it can, and the briefing says the reconstruction is partial.

**`plan.md`** — the Progress table, the Discovered Services table, and every step whose `**Status:**` is `In Progress` or `Blocked`, in full including its note. Then the first `Pending` step after them, since that is where work resumes if nothing is in flight. Do not read every phase.

**`digest.md`** — the Description and Acceptance Criteria, for the two or three sentences of the briefing that say what the work actually is. Skip the metadata table, the attachments and the discussion.

**`artifacts/`** — the `README.md` of the in-flight step, of the next step, of `shared/`, and of `planning/` where they exist. These hold measurements taken against live systems, which are the one thing here that cannot be regenerated. **Never re-run a probe whose captured output is already on disk**; a resume that re-measures what a prior session already established has failed at its job.

### 3. Establish where the work stopped

Prefer the journal's `**Stopped at:**` and `**Next:**` lines. They were written by the session that was there.

When `journal.md` is absent or its newest entry predates later work, reconstruct instead, and say in the briefing that it is a reconstruction:

- The in-flight step is the first step that is `In Progress` or `Blocked`; failing that, the first `Pending` step after the last `Done` one.
- Modification times under `artifacts/` and the branch's recent commit subjects indicate what was most recently worked on.
- Uncommitted changes in the working tree indicate what was in flight when the session ended.

If no journal exists at all, say so plainly in the briefing and recommend `/az-workitem-checkpoint {id}` at the end of this session, so the next resume does not have to guess again.

### 4. Read the live git state

Locate the shared collector relative to this skill file — it lives in the sibling `az-workitem-common` directory, alongside `ado_auth.py`:

```
skills/az-workitem-common/collect-git-state.py
```

Run it from the repository the work is being done in. It writes nothing.

```bash
python "{path-to-az-workitem-common}/collect-git-state.py"
```

Two comparisons matter more than the raw output:

- **Is this even the right repository?** Compare `repo_name` and `branch` against the journal's `**Where:**` line. A mismatch is the most likely reason a resume goes wrong, because every path in `plan.md` is repo-relative and will silently resolve against the wrong tree. Say so at the top of the briefing rather than burying it:

  > You are in `{repo}` on `{branch}`, but #{id} was last worked on in `{recorded repo}` on `{recorded branch}`. Switch before continuing.

- **How far has the base moved?** `base_commits_not_merged` is how many commits the base branch gained while this branch sat idle. After days away it is often large, and it is the reason a plan written against an older tree may no longer apply cleanly. Report it; do not act on it.

If `is_repo` is `false`, report that no repository was found in the current directory and brief from the files alone.

### 5. Check whether the work item drifted

Run the delta check, which lives beside this skill:

```bash
python "{path-to-skill}/check-work-item-delta.py" --id {id}
```

It reads the local `raw/raw.json`, compares a handful of fields plus the comment count against live ADO, and writes nothing. Organization and project come from `raw.json`, so no arguments beyond `--id` are needed.

Interpret the exit code:

- **0** — the local copy is current. Say nothing beyond one line confirming it.
- **2** — the work item changed. Report each field change, and each new comment with its author, age, and snippet. Then recommend, without running either:

  > `digest.md` predates these changes. Run `/az-workitem-fetch {id}` and then `/az-workitem-digest {id}` to fold them in before continuing.

  A new comment answering an open question from the journal is the single most valuable thing this check can surface — call that out explicitly when it happens.

- **1** — the check could not be made (no `raw.json`, expired `az login`, no network). Report the reason in one line and continue with the rest of the briefing. A failed drift check does not block a resume.

### 6. Print the briefing

One message, in this shape. Omit any section that has no content — an empty heading is noise. Keep it scannable: this is read by someone who has forgotten everything and wants to start working.

```
Resuming #{id} — {title}
{type} · {state} · last touched {N} days ago ({date of newest journal entry or file})

The work
  {2–3 sentences from digest.md: the goal, and what done looks like}

Where you stopped
  Phase {N} ({name}) · Step {N}.{M} — {status}
  {the Stopped at line, or the reconstruction}

Next
  {the Next line, verbatim from the journal where there is one}

Progress
  [x] Phase 1  {name}
  [~] Phase 2  {name}   ← here
  [ ] Phase 3  {name}
  {N} / {N} phases done · ~{X} hrs estimated remaining

Code
  {repo} @ {branch} · HEAD {sha} · {N} commits ahead of {base}
  Working tree: {clean | N modified, N untracked — uncommitted}
  {base} has moved {N} commits since you branched
  {N} stash(es): {subject}

Carried forward
  • {decision} — {why} (Step {N}.{M})
  • Blocker: {what} — {what would clear it} (Step {N}.{M})
  • Question: {what} — {who can answer} (Step {N}.{M})

Changed while you were away
  • {field}: {before} → {after}
  • {N} new comments — {author}, {N} days ago: "{snippet}"
  → {the fetch/digest recommendation}
```

Rules:

- Collapse a long Progress table: every `Done` and `Blocked` phase, the in-flight phase, and the next two `Pending` ones. Summarize the rest as `… {N} more phases pending`.
- Quote the journal's `**Next:**` line verbatim. Do not improve it — it was written with context this session does not have.
- Mark reconstructed facts as reconstructed. Never present an inference as a record.
- Do not print the plan, the digest, or a file's contents wholesale. This is a briefing, not a dump.

### 7. Offer the next action, then stop

Close with the options that fit what was found, and **wait**:

> Ready to continue. I can:
> • `/az-workitem-implement {id} {N}` — pick up Phase {N} where it stopped
> • `/az-workitem-fetch {id}` then `/az-workitem-digest {id}` — fold in the {N} ADO changes first
> • `/az-workitem-plan {id}` — review or revise the plan before continuing
>
> Or tell me what you would rather do.

Do not start implementing, fetching, or planning. Resuming is about restoring context; the decision about what to do with it is the user's.

---

## Constraints

- **Read-only. Write nothing** — no code, no `journal.md`, no `plan.md`, no artifacts. Use `/az-workitem-checkpoint` to record state and `/az-workitem-implement` to change code
- Run only read-only commands: `collect-git-state.py`, `check-work-item-delta.py`, and reads of the files named above. Never `git fetch`, `git pull`, `git checkout`, `git stash`, or any command that changes repository state
- Never run a script under `artifacts/` — a captured output already on disk is the answer, and re-running a probe against a live system needs the user's approval in the session that needs it
- **Never read `raw.json` for work item content** — `digest.md` is the source of truth. `check-work-item-delta.py` reads `raw.json` for comparison only, which is not the same thing
- Never chain into another skill automatically — step 7 offers, the user chooses
- Never present a reconstruction as a record; label it
- Do not correct `plan.md` even when it is visibly stale — report the discrepancy and let `/az-workitem-checkpoint` or `/az-workitem-plan` fix it
- Keep the briefing to one message; a resume that takes as long to read as the plan itself has failed
