---
name: ticket-resume
description: Rebuilds the context for a ticket in a fresh session — reads journal.md, plan.md, digest.md and prior artifacts, inspects the live git state, and checks whether the ticket changed since it was last fetched. Outputs a briefing ending in the single next action.
argument-hint: "[ref]"
allowed-tools: Read Grep Glob Bash(python *ticket.py:*) Bash(python *collect-git-state.py:*)
---

Rebuilds a ticket's context in a fresh session. Everything needed is on disk — the digest, the plan, the artifacts, the journal — but two things no file holds have usually drifted since: the state of the worktree, and the ticket itself. This skill reads it all back and prints one briefing: what the work is, where it stopped, the next action, what the code looks like now, and what changed at the source while attention was elsewhere.

End state: one briefing that ends by offering the next action, nothing on disk changed, and — where no session context was set — the ticket's product adopted as the session context.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file                                             |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`[ref]`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Absent, Step 1 lists the tickets on disk and asks; `{ref}` is the one it settles on.

---

## Ground rules

1. **Write nothing.** No code, no `journal.md`, no `plan.md`, no artifacts — `/ticket-checkpoint` records state and `/ticket-implement` changes code.
2. **Run only read-only commands:** `collect-git-state.py`, `ticket.py` `resolve`, `list` and `drift`, and reads of the files the steps name. Never `git fetch`, `pull`, `checkout`, `stash` or any command that changes repository state.
3. **Never run a script under `artifacts/`.** A captured output already on disk is the answer; re-running a probe against a live system needs the user's approval in the session that needs it.
4. **Never read the source's raw data for ticket content.** `digest.md` is the source of truth; the drift check reads the snapshot for comparison only.
5. **Never correct `plan.md`, even when it is visibly stale.** Report the discrepancy and let `/ticket-checkpoint` or `/ticket-plan` fix it.
6. **Never chain into another skill.** Step 5 recommends and Step 7 offers; the user chooses.
7. **Label every reconstruction.** Never present an inference as a record.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below that takes one — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

**When no `[ref]` was given, ask. Never guess, and never infer it from the branch name** — a guess that attaches a session to the wrong ticket is silent, and it is the journal, the one unregenerable file here, that it would corrupt. Run `python "{skills}/ticket-common/ticket.py" list [--context {context}]` and print the candidates as a table with **Product** and **Source** columns, each with its title, type, the date of its newest journal entry, its phase progress from `plan.md`, and when it was last touched — most recently touched first. With a session context, print only the tickets whose `in_context` is true, and say how many are outside it (`outside_context`) with an offer to show them all. Then ask which to resume. The listing is half the problem this skill solves: "which one was I in the middle of".

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require ticket_dir [--context {context}]
```

- **Exit 0** → continue with the paths, capabilities, type and `ticket.json` it returns, and its `qualified_ref` for every later `ticket.py` call. Every path is absolute.
- **Any non-zero exit** → report the message and its hint verbatim, and stop.

Open `ticket-common/RESOLUTION.md` only when the output is disputed. Then settle the briefing's first line:

- **No session context is set** → adopt the ticket's product: resuming a ticket is the user choosing where this session works. The first line is `Ticket context:`, the product in backticks, then `(adopted from` and the qualified reference `)`. Every later skill in this session uses it exactly as if `/ticket-context` had been run with that product.
- **A session context is set** → never replace it. The first line is `Ticket context: {context}` as usual; where the ticket is outside it (`outside_context`), say in the briefing that it is filed under its own product.

### Step 2 — Read what past sessions recorded

Read, in this order, and stop reading a file once the briefing has what it needs:

**`journal.md`** — the newest entry in full, and enough of the two before it to see decisions and blockers that are still open. This is the primary source: it is the only file that records *why* things are the way they are. If it does not exist, note that and continue — Step 3 reconstructs what it can, and the briefing says the reconstruction is partial.

**`plan.md`** — the Progress table, the Workspace section, and every step whose `**Status:**` is `In Progress` or `Blocked`, in full including its note. Then the first `Pending` step after them, since that is where work resumes if nothing is in flight. Do not read every phase. The status vocabulary is in `ticket-common/STATUS.md` if a line needs interpreting.

**`digest.md`** — the Description and Acceptance Criteria, for the two or three sentences of the briefing that say what the work actually is. Skip the metadata table, the attachments and the discussion.

**`artifacts/`** — the `README.md` of the in-flight step, of the next step, of `shared/`, and of `planning/` where they exist. These hold measurements taken against live systems, which are the one thing here that cannot be regenerated. **Never re-run a probe whose captured output is already on disk**; a resume that re-measures what a prior session already established has failed at its job. `ticket-common/ARTIFACTS.md` has the layout.

### Step 3 — Establish where the work stopped

Prefer the journal's `**Stopped at:**` and `**Next:**` lines. They were written by the session that was there.

When `journal.md` is absent or its newest entry predates later work, reconstruct instead, and say in the briefing that it is a reconstruction:

- The in-flight step is the first step that is `In Progress` or `Blocked`; failing that, the first `Pending` step after the last `Done` one.
- Modification times under `artifacts/` and the branch's recent commit subjects indicate what was most recently worked on.
- Uncommitted changes in the worktree indicate what was in flight when the session ended.

If no journal exists at all, say so plainly in the briefing and recommend `/ticket-checkpoint {ref}` at the end of this session, so the next resume does not have to guess again.

### Step 4 — Read the live git state

Run the shared collector from the worktree the work is being done in. It writes nothing. Its terms are the ones in `ticket-common/GLOSSARY.md`.

```bash
python "{skills}/ticket-common/collect-git-state.py"
```

Two comparisons matter more than the raw output:

- **Is this even the right worktree?** Compare `repository`, `worktree` and `branch` against the journal's `**Where:**` line, and check that the worktree is one the Workspace section of `plan.md` lists. A mismatch is the most likely reason a resume goes wrong, because every `**Target:**` in `plan.md` is relative to a worktree the Workspace section names, and resolves silently against whichever one is current. Say so at the top of the briefing rather than burying it: name the current repository, branch and worktree and the recorded ones, and tell the user to switch before continuing.

- **How far has the base moved?** `base_commits_not_merged` is how many commits the base branch gained while this branch sat idle. After days away it is often large, and it is the reason a plan written against an older base may no longer apply cleanly. Report it; do not act on it.

If `is_repository` is `false`, report that the invocation directory is outside every repository and brief from the files alone.

### Step 5 — Check whether the ticket drifted

Where the resolver reported `capabilities.drift` is **false**, skip this step and say so in one line in the briefing — that source cannot tell whether the ticket moved, and a gap reported is worth more than a check silently omitted.

Otherwise run:

```bash
python "{skills}/ticket-common/ticket.py" drift "{qualified_ref}"
```

It is read-only against both the source and the local snapshot. What it compares, and why some fields are reported as context rather than as diff rows, is in `ticket-providers/{source}/drift.md` — read that only when a result needs interpreting.

Interpret the exit code:

- **0** — the local copy is current. Say nothing beyond one line confirming it.
- **2** — the ticket changed. Report each field change, and each new comment with its author, age, and snippet. Then recommend, without running either, `/ticket-fetch` and then `/ticket-digest` on the ticket: `digest.md` predates these changes.

  A new comment answering an open question from the journal is the single most valuable thing this check can surface — call that out explicitly when it happens.

- **1** — the check could not be made. Report the reason in one line and continue with the rest of the briefing. A failed drift check does not block a resume.

### Step 6 — Print the briefing

One message, filled from [`briefing.md`](./briefing.md): fill every `{camelCase}` placeholder, and replace every `<!-- guidance -->` comment with the content it asks for. Omit any section that has no content — an empty heading is noise. Keep it scannable: this is read by someone who has forgotten everything and wants to start working.

Rules:

- Link `{title}` to `ticket.json`'s `url`. Where it is `null`, print the title as plain text — this source has no web address, and a broken link is worse than none.
- Collapse a long Progress table: every `Done` and `Blocked` phase, the in-flight phase, and the next two `Pending` ones. Summarize the rest as `… {N} more phases pending`.
- Quote the journal's `**Next:**` line verbatim. Do not improve it — it was written with context this session does not have.
- Mark reconstructed facts as reconstructed. Never present an inference as a record.
- Do not print the plan, the digest, or a file's contents wholesale. This is a briefing, not a dump.

### Step 7 — Offer the next action, then stop

The briefing closes with `briefing.md`'s offer. Keep only the options that fit what was found — the fetch option only where the source can fetch and Step 5 found changes — and wait.

Do not start implementing, fetching, or planning. Resuming is about restoring context; the decision about what to do with it is the user's.
