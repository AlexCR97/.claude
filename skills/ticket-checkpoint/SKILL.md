---
name: ticket-checkpoint
description: Records the current session's state on a ticket as an entry in journal.md — where the code is, what was done, what was decided and why, what is blocking, and the single next action. Run it before switching away from a ticket so a later /ticket-resume can pick the work up.
argument-hint: "[ref] [note]"
allowed-tools: Read Write Edit Bash(python *ticket.py:*) Bash(python *collect-git-state.py:*)
---

Records the current session's state on a ticket as a new entry at the top of its `journal.md` — where the code is, what was done, what was decided and why, what is blocking, and the single next action — so a later `/ticket-resume` can pick the work up. The plan records what the work is; it cannot record what a session learned, and that dies with the session unless this skill writes it down. It is the only skill that writes `journal.md`, so an unrecorded session leaves nothing behind but its step statuses.

End state: one new entry at the top of `journal.md`, every existing entry untouched, any stale `**Status:**` line in the phases this session worked corrected and the plan re-synced, and nothing else changed.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file                                             |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`[ref]`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Step 1 settles `{ref}` from it, from this session's ticket, or by asking.
- **`[note]`** — free text, quoted, the user wants recorded (e.g. `"stopping to review the PR for 18201"`). Fold it into the entry; never let it replace the entry's own content.

---

## Ground rules

1. **Record state; change no code.** Never create, edit or delete a source code file.
2. **Write only `journal.md`**, plus the `**Status:**` lines Step 6 corrects in the phase files this session worked, and the generated block `ticket.py plan-sync` rewrites. Never touch another session's phase, `digest.md`, `raw/` or anything under `artifacts/`.
3. **Run only read-only commands.** `collect-git-state.py` and `ticket.py` are read-only; never run `git fetch`, `pull`, `add`, `stash` or any other command that changes repository state — the developer decides when to commit, stash or push.
4. **Record local state only.** Never re-fetch the ticket or check its source; `/ticket-resume` is what checks for drift.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below that takes one and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

Take `[ref]` from the invocation, or else the ticket this session has been working on — a `/ticket-implement` or `/ticket-resume` run earlier in the conversation, or a plan already read. Never infer it from the branch name: a wrong guess attaches a session's account of itself to the wrong ticket, and `journal.md` is the one file nothing can regenerate.

**Failing both, ask. Never guess.** Run `python "{skills}/ticket-common/ticket.py" list [--context {context}]` and print the candidates as a table with **Product** and **Source** columns, each with its title and when it was last touched, newest first. With a session context, print only the tickets whose `in_context` is true, and say how many are outside it with an offer to show them all. Then ask which to checkpoint.

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require ticket_dir [--context {context}]
```

- **Exit 0, and `outside_context` is true** → ask whether to checkpoint it anyway, naming its product and the session context, defaulting to no. On yes, continue; on no, stop. A session working in one product while checkpointing a ticket in another is exactly how an entry lands on the wrong ticket.
- **Exit 0** → continue with the paths, type and `ticket.json` it returns. Every path is absolute.
- **Any non-zero exit** → report the message and its hint verbatim, and stop.

Open `ticket-common/RESOLUTION.md` only when the output is disputed.

### Step 2 — Collect the git state

Run the shared collector from the worktree the work is being done in:

```bash
python "{skills}/ticket-common/collect-git-state.py"
```

It reports the repository and the path of its worktree, the branch, HEAD, the base branch and merge base, commits ahead of base, commits the base has gained since, the worktree's uncommitted-change counts, and any stashes. It writes nothing, and it interprets nothing — `branch` is a plain string. Its terms are the ones in `ticket-common/GLOSSARY.md`.

If `is_repository` is `false`, record `**Where:** not in a repository` and carry on — an entry without git coordinates is still worth far more than no entry.

### Step 3 — Reconstruct what this session did

This is the step that carries the skill. Everything else on disk is already recoverable; this is not.

Work back through the conversation and collect:

- **Done** — what actually changed: files created or edited, behavior that now works. Describe outcomes, not attempts. Where a change is not yet committed, say so.
- **Decisions** — every choice made in dialogue, with its *why* and what it was chosen over. A decision whose rationale is missing will be re-litigated in the next session, which is the exact cost this skill exists to avoid.
- **Inferences** — anything implemented on an assumption because the plan was underspecified, and the basis for it.

`ticket-implement` ends each run by reporting its decisions and inferences in chat precisely so that this step can find them. Where such a report is in this conversation, carry both lists over **verbatim** rather than paraphrasing them — that report is the only record of them, since implement does not write to this file.

Continue collecting:

- **Open questions** — what is unresolved, and who or what can resolve it.
- **Blockers** — what is preventing progress, and what would clear it.
- **Stopped at** — the step in flight and its honest state: what works, what does not, what is half-done. A step that is 80% finished must not read as complete.

Cross-check against the phase files of the phases this session worked: name the phase and step each item belongs to, so a later reader can jump straight to it. If the session's work has left a step's `**Status:**` line wrong, note it for Step 6. Several sessions may be working this ticket at once, each on its own phase; this entry covers only the phases this one touched.

Where the resolved type's file in `ticket-types/` names something the run had to produce or report — a repro that was re-run, a test suite that must pass unmodified, a written finding — record what actually happened to it. That is the fact a later session cannot reconstruct.

### Step 4 — Establish the next action

The `**Next:**` line is the highest-value line in the entry, and the one a resume reads first. It must be specific enough to act on without re-reading the plan — a file and an action, not a phase name.

Good:

> **Next:** Fix the DI registration for `IUserAuthorizationReader` in `BenchmarkSetup.cs:41`, then run Step 2.7's harness and capture the output.

Not good:

> **Next:** Continue Phase 2.

Derive it from the session where the session makes it obvious. Where it does not — the session ended on an open question, or several things could reasonably come next — ask the user rather than guessing: give the best inference, and ask them to correct or accept it. Wait for the answer. A wrong `**Next:**` line is worse than an absent one, because it will be trusted.

Where the phases this session worked are done but others are Ready, name one — `**Next:** Phase 4 (API endpoint) is Ready: start it with /ticket-implement {ref} 4.` When nothing is pending — every phase done — write that plainly: `**Next:** Nothing pending; all phases complete. Awaiting review.`

### Step 5 — Write the entry

Read [`journal-template.md`](./journal-template.md) and follow its structure: fill every `{camelCase}` placeholder, and replace every `<!-- guidance -->` comment with the content it asks for.

**If `journal.md` does not exist**, create it with the header from the template — the title line and the note about entry ordering — then write this entry as the first one. `{ticketUrl}` is `ticket.json`'s `url`; where it is `null`, write the title as plain text rather than a broken link.

**If it exists**, re-read it immediately before writing, then insert the new entry immediately after the header block, above whatever entry is newest now, separated by `---`. Another session working a parallel phase may have checkpointed since this one last looked, and writing back a copy read earlier would erase its entry. Entries run newest first so the current state is the top of the file rather than the end of a growing scroll.

Rules for an entry:

- Timestamp the heading in **UTC** as `YYYY-MM-DD HH:MM` — `{timestamp}` — matching the `> Generated on` convention in `digest.md` and `plan/plan.md`.
- Name every phase the session worked, and the step it stopped in, so the heading alone locates the work — and, with several sessions on one ticket, tells their entries apart.
- `**Where:**`, `**Worktree state:**`, `**Stopped at:**` and `**Next:**` are always present. Where a fact is unavailable, say so explicitly rather than omitting the line.
- Omit any of the `### Done`, `### Decisions`, `### Inferences`, `### Open questions` and `### Blockers` sections that would be empty. Do not pad an entry with a heading over nothing.
- **Never edit or delete an existing entry.** A session's account of itself is not regenerable — the one thing here that no later run can reconstruct. A correction is a new entry saying what it corrects.
- **Write a reference to another ticket the way a stored one is written**: short (`{source}:{id}`) when it is filed in the same product as this ticket, qualified (`{namespace}/{product}/{source}:{id}`) when it is not — `ticket-common/RESOLUTION.md` → *How a reference resolves*.
- **Do not record where this ticket is filed.** Its directory already says so, and an entry that did would go stale on the first `/ticket-move` with no way to correct it.
- Keep it factual and short. An entry is read in a hurry, by someone who has forgotten everything.

### Step 6 — Reconcile the phase files' status lines

If the session left a step's status stale, correct only its `**Status:**` line in its phase file — nothing else, and only in a phase this session worked:

- A step that was started and is not finished → `In Progress`, with a note saying what remains
- A step that cannot proceed → `Blocked`, with a note saying what is blocking
- A step finished this session → `Done`

The vocabulary and the note rules are in `ticket-common/STATUS.md`. Then sync, which re-derives every phase's status from its steps and rewrites the Progress table:

```bash
python "{skills}/ticket-common/ticket.py" plan-sync "{ref}" [--context {context}]
```

If no status line needs changing, leave the phase files untouched and skip the sync.

### Step 7 — Report

Report in two lines at most. Do not print the entry body in chat — it was just written to a file the user can open. The first line names the ticket, the `journal.md` path, the phase and step, and the Next line condensed; the second names each step Step 6 changed and its new status, or says the plan is unchanged.
