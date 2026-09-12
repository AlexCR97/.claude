---
name: ticket-resume
description: Rebuilds the context for a ticket in a fresh session — reads journal.md, plan.md, digest.md and prior artifacts, inspects the live git state, and checks whether the ticket changed since it was last fetched. Outputs a briefing ending in the single next action. Read-only; makes NO changes.
argument-hint: "<[source:]id>"
allowed-tools: Read Grep Glob Bash(python:*)
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md` | everything specific to what shape the work is | only the **resolved** type's file |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

**`allowed-tools` is set on this skill deliberately.** Its headline promise is that it makes no changes, and its first constraint is "write nothing". An allowlist is the only thing that makes that mechanically true rather than merely stated.

---

## Purpose

A ticket gets put down and picked up days later in a new session that knows nothing about it. Everything needed is already on disk — the digest, the plan, the artifacts, the journal — but reading it back into context by hand is slow and easy to do incompletely, and two things no file can hold have usually drifted in the meantime: the state of the working tree, and the ticket itself.

This skill assembles all of it into one briefing: what the work is, where it stopped, what the next action is, what the code looks like right now, and what changed at the source while attention was elsewhere.

**Read-only.** It writes nothing, changes no code, and starts no work — it ends by offering the next action, and waits.

---

## Input

```
/ticket-resume <[source:]id>
```

`{ref}` — the ticket, optionally prefixed with its source (`ado:18159`, `gh:42`, `local:auth-fix`). A bare id resolves against what is on disk. When omitted, **ask** — see step 1.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the ticket

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require ticket_dir
```

Everything below uses the paths, capabilities, type and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

**When no ref was given, ask. Never guess.** Run `ticket.py list` and print the candidates as a table with a **Source** column, each with its title, type, the date of its newest journal entry, its phase progress from `plan.md`, and when it was last touched — most recently touched first. Then ask which to resume.

That listing is worth printing whenever the user does not name a ticket, because "which one was I in the middle of" is half the problem this skill solves.

There is no inference from the branch name, and there must not be: a guess that attaches a session to the wrong ticket is silent, and it is the journal — the one unregenerable file here — that it would corrupt.

### 2. Read what past sessions recorded

Read, in this order, and stop reading any file as soon as you have what the briefing needs:

**`journal.md`** — the newest entry in full, and enough of the two before it to see decisions and blockers that are still open. This is the primary source: it is the only file that records *why* things are the way they are. If it does not exist, note that and continue — step 3 reconstructs what it can, and the briefing says the reconstruction is partial.

**`plan.md`** — the Progress table, the Discovered Services table, and every step whose `**Status:**` is `In Progress` or `Blocked`, in full including its note. Then the first `Pending` step after them, since that is where work resumes if nothing is in flight. Do not read every phase. The status vocabulary is in `ticket-common/STATUS.md` if a line needs interpreting.

**`digest.md`** — the Description and Acceptance Criteria, for the two or three sentences of the briefing that say what the work actually is. Skip the metadata table, the attachments and the discussion.

**`artifacts/`** — the `README.md` of the in-flight step, of the next step, of `shared/`, and of `planning/` where they exist. These hold measurements taken against live systems, which are the one thing here that cannot be regenerated. **Never re-run a probe whose captured output is already on disk**; a resume that re-measures what a prior session already established has failed at its job. `ticket-common/ARTIFACTS.md` has the layout.

### 3. Establish where the work stopped

Prefer the journal's `**Stopped at:**` and `**Next:**` lines. They were written by the session that was there.

When `journal.md` is absent or its newest entry predates later work, reconstruct instead, and say in the briefing that it is a reconstruction:

- The in-flight step is the first step that is `In Progress` or `Blocked`; failing that, the first `Pending` step after the last `Done` one.
- Modification times under `artifacts/` and the branch's recent commit subjects indicate what was most recently worked on.
- Uncommitted changes in the working tree indicate what was in flight when the session ended.

If no journal exists at all, say so plainly in the briefing and recommend `/ticket-checkpoint {ref}` at the end of this session, so the next resume does not have to guess again.

### 4. Read the live git state

Run the shared collector from the repository the work is being done in. It writes nothing.

```bash
python "{skills}/ticket-common/collect-git-state.py"
```

Two comparisons matter more than the raw output:

- **Is this even the right repository?** Compare `repo_name` and `branch` against the journal's `**Where:**` line. A mismatch is the most likely reason a resume goes wrong, because every path in `plan.md` is repo-relative and will silently resolve against the wrong tree. Say so at the top of the briefing rather than burying it:

  > You are in `{repo}` on `{branch}`, but {ref} was last worked on in `{recorded repo}` on `{recorded branch}`. Switch before continuing.

- **How far has the base moved?** `base_commits_not_merged` is how many commits the base branch gained while this branch sat idle. After days away it is often large, and it is the reason a plan written against an older tree may no longer apply cleanly. Report it; do not act on it.

If `is_repo` is `false`, report that no repository was found in the current directory and brief from the files alone.

### 5. Check whether the ticket drifted

Where the resolver reported `capabilities.drift` is **false**, skip this step and say so in one line in the briefing — that source cannot tell you whether the ticket moved, and a gap reported is worth more than a check silently omitted.

Otherwise run:

```bash
python "{skills}/ticket-common/ticket.py" drift "{source}:{id}"
```

It is read-only against both the source and the local snapshot. What it compares, and why some fields are reported as context rather than as diff rows, is in `ticket-providers/{source}/drift.md` — read that only when a result needs interpreting.

Interpret the exit code:

- **0** — the local copy is current. Say nothing beyond one line confirming it.
- **2** — the ticket changed. Report each field change, and each new comment with its author, age, and snippet. Then recommend, without running either:

  > `digest.md` predates these changes. Run `/ticket-fetch {ref}` and then `/ticket-digest {ref}` to fold them in before continuing.

  **A new comment answering an open question from the journal is the single most valuable thing this check can surface — call that out explicitly when it happens.**

- **1** — the check could not be made. Report the reason in one line and continue with the rest of the briefing. A failed drift check does not block a resume.

### 6. Print the briefing

One message, in this shape. Omit any section that has no content — an empty heading is noise. Keep it scannable: this is read by someone who has forgotten everything and wants to start working.

```
Resuming {ref} — {title}
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

- Link the title to `ticket.json`'s `url`. Where it is `null`, print the title as plain text — this source has no web address, and a broken link is worse than none.
- Collapse a long Progress table: every `Done` and `Blocked` phase, the in-flight phase, and the next two `Pending` ones. Summarize the rest as `… {N} more phases pending`.
- Quote the journal's `**Next:**` line verbatim. Do not improve it — it was written with context this session does not have.
- Mark reconstructed facts as reconstructed. Never present an inference as a record.
- Do not print the plan, the digest, or a file's contents wholesale. This is a briefing, not a dump.

### 7. Offer the next action, then stop

Close with the options that fit what was found, and **wait**. Offer the fetch option only where the source can fetch:

> Ready to continue. I can:
> • `/ticket-implement {ref} {N}` — pick up Phase {N} where it stopped
> • `/ticket-fetch {ref}` then `/ticket-digest {ref}` — fold in the {N} changes first
> • `/ticket-plan {ref}` — review or revise the plan before continuing
>
> Or tell me what you would rather do.

Do not start implementing, fetching, or planning. Resuming is about restoring context; the decision about what to do with it is the user's.

---

## Constraints

- **Read-only. Write nothing** — no code, no `journal.md`, no `plan.md`, no artifacts. Use `/ticket-checkpoint` to record state and `/ticket-implement` to change code
- Run only read-only commands: `collect-git-state.py`, `ticket.py resolve` / `list` / `drift`, and reads of the files named above. Never `git fetch`, `git pull`, `git checkout`, `git stash`, or any command that changes repository state
- Never run a script under `artifacts/` — a captured output already on disk is the answer, and re-running a probe against a live system needs the user's approval in the session that needs it
- **Never read the source's raw data for ticket content** — `digest.md` is the source of truth. The drift check reads the snapshot for comparison only, which is not the same thing
- **Never infer the ticket from the branch name or from anything else.** Use the argument, or ask
- Never chain into another skill automatically — step 7 offers, the user chooses
- Never present a reconstruction as a record; label it
- Do not correct `plan.md` even when it is visibly stale — report the discrepancy and let `/ticket-checkpoint` or `/ticket-plan` fix it
- Keep the briefing to one message; a resume that takes as long to read as the plan itself has failed
