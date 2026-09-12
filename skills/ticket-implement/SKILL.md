---
name: ticket-implement
description: Follow-up to ticket-plan. Reads plan.md for a ticket and implements one, several, or all phases by making real code changes. Tracks step status (Pending, In Progress, Blocked, Done) in plan.md as it goes. On completion, reports what the run produced and what was inferred.
argument-hint: "<[source:]id> [phases]"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | **none.** See below |
| `ticket-types/{type}.md` | everything specific to what shape the work is | only the **resolved** type's file |

**This skill is source-agnostic: it reads no provider file at all.** By the time it runs, everything the ticket said is in `digest.md` and everything the work is, is in `plan.md`. If this skill ever needs a provider file, the abstraction has leaked — treat that as a bug to report rather than a file to open.

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** Treat each type file as present-or-absent independently, and never substitute another type's module for a missing one.

No `allowed-tools` here: this skill's whole purpose is to change code and build it, so an allowlist would be theatre.

---

## Input

```
/ticket-implement <[source:]id> [{phases}]
```

- `{ref}` — required. The ticket, optionally prefixed with its source. If none is given, ask for it before proceeding.
- `{phases}` — optional. One of:
  - A comma-separated list of phase numbers: `1`, `1,3`, `2,3,4`
  - The literal string `all` — runs every pending phase in order
  - Omitted — the skill shows the current progress table and prompts the user to specify

---

## Step Status

The four-value vocabulary, the note rules, and the table deriving a phase's Progress row from its steps are in **`ticket-common/STATUS.md`**. Read it rather than restating it.

Two things it says that this skill leans on hardest:

- **Mark a step `In Progress` before its first edit.** A session can end at any moment — an interrupt, a context switch, a closed terminal — and only what is already on disk survives it. A status written after the fact is a status that is sometimes never written at all.
- **A note is the whole of what this skill records about *why* a step is where it is.** Make it carry its weight in one line. The fuller account of a session — decisions, rationale, the next action — is `ticket-checkpoint`'s to write, from this session's conversation, when attention leaves the ticket.

---

## Artifacts

The layout, the placement rules, the capture-naming convention, the append-only rule, the renumbering pass and the run-approval rule are all in **`ticket-common/ARTIFACTS.md`**. Read it before producing any file that is not a change to the codebase.

Two boundaries matter here: `artifacts/planning/` belongs to `ticket-plan` — **read it, never write to it**; this skill writes only `artifacts/step-{N}.{M}/` and `artifacts/shared/`.

`journal.md` is the per-session work log, and it is **out of scope for this skill: never read it, never write to it.** It belongs to `ticket-checkpoint`, which writes it when attention leaves the ticket, and to `ticket-resume`, which reads it back at the start of the next session. By the time this skill runs, `ticket-resume` has already loaded that history into the session, so reading it again would only spend context on what is already here.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the ticket

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require plan
```

Everything below uses the paths and type it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `plan` requirement means there is nothing to implement; the hint names the skill that fixes it.

### 2. Read the type's completion rule, then the plan

Read **`ticket-types/{type}.md`**, specifically its *"What done means"* and *"What implement must produce"* sections. **They define what this run has to show for itself before any phase may be reported complete**, and they are the only thing that varies here by type. Take them seriously in both directions: a type whose deliverable is a document is not an incomplete run, and a type whose invariant was broken is not a run that merely needs a note.

Then parse `plan.md` and extract:

- The **Progress table** — phase names, estimates, and current status (`[ ] Pending`, `[~] In Progress`, `[!] Blocked`, `[x] Done`)
- Each **Phase section** — its scope, services touched, and step sub-sections (`### Step {N}.{M}`, each with a `**Status:**`, `**Target:**`, and `**Artifacts:**` line)
- The **Discovered Services table** — maps service names to relative paths and technology stack; used in step 9

Then list the ticket's `artifacts/`. Every `**Artifacts:**` line that names a directory should have one on disk, and every directory on disk should be named by some step's `**Artifacts:**` line. Where they disagree, trust the disk and correct `plan.md`.

A step marked `In Progress` or `Blocked` was left mid-flight by an earlier session. Its `**Status:**` note is what this skill goes on, together with anything about that session already in this conversation — `ticket-resume` puts it there when it briefs the session. Do not open `journal.md` to look for more.

### 3. Resolve which phases to implement

If `{phases}` was provided as `all`, collect every phase whose status is not `[x] Done`.

If `{phases}` was provided as a comma-separated list, collect those phase numbers — but **skip any that are already `[x] Done`** and warn the user for each skipped one:

> Phase {N} ({name}) is already marked done — skipping.

A phase whose status is `[!] Blocked` is **not** skipped automatically, but it is not run silently either. Report the blocking step and its note, and ask before proceeding:

> Phase {N} ({name}) is blocked at Step {N}.{M} — {note}. Has that been resolved? I can implement the phase's other steps, or wait.

Wait for the answer. Implementing straight through a blocker usually produces work that has to be redone once the real answer arrives.

A phase holding an `In Progress` step resumes at that step rather than restarting the phase — its `**Status:**` note says what is already done.

If `{phases}` was not provided, print the current progress table and ask:

> Which phases would you like to implement? Enter phase numbers separated by commas, or "all" for all pending phases.

Wait for the response, then resolve as above.

If no phases remain after filtering out done ones, stop:

> All specified phases are already complete. Nothing to implement.

---

## Implementation Loop

For each resolved phase, **in ascending order**, run the following sub-steps.

### 4. Read the phase steps

Re-read the phase section from `plan.md`. Extract each step sub-section (`### Step {N}.{M}`), its `**Status:**`, `**Target:**`, and `**Artifacts:**`.

Skip any step already marked `Done`. Resume — do not restart — any step marked `In Progress`: read its `**Status:**` note first and take what it says was already done as done. Re-doing a completed half of a step is how a resumed session quietly reverts a decision the previous one made.

For every step whose `**Artifacts:**` line is not `—`, **read that step's artifacts directory before implementing anything**. A previous run left those files there because they carry something the plan alone does not: a measurement, a query result, an extract, a correction. Treat what they establish as fact, and never re-run a probe whose output is already on disk. Also read `artifacts/shared/` and `artifacts/planning/` if they exist — a findings document in either may carry the premise the step was built on, or a later correction to it.

If any step references a file or class that does not exist yet, note it as a **new file** to be created. If any step is ambiguous or underspecified:

1. First consult `digest.md` — the **Acceptance Criteria**, **Description**, and **Discussion** sections often resolve ambiguity.
2. If still unclear, use best judgment based on the patterns already established in the relevant service. Record what was inferred — it will be included in the completion report.

### 5. Load coding standards

Before writing any code, internalize the following global rules (they apply to all languages unless a local convention overrides them):

- `~/.claude/rules/csharp-conventions.md` — C# naming, encapsulation, async patterns, DDD conventions
- `~/.claude/rules/design-patterns.md` — creational, structural, and behavioral patterns
- `~/.claude/rules/solid-principles.md` — SOLID principles

For each service being modified, also read enough of the existing code to identify:

- Naming conventions in use (file names, class names, method names)
- Folder structure and where new files of each type belong
- Patterns already established (e.g. how repositories are structured, how DTOs are named)

Local codebase patterns take precedence over global rules where they differ, **except** where the global rules explicitly prohibit a pattern (e.g. blocking async void, enforcing `private readonly` dependencies).

### 6. Implement the steps

Work through each step in the phase sequentially. For every step:

#### Modifying an existing file

1. Read the file in full before making any change.
2. Make targeted edits — never replace the entire file content.
3. Preserve all unrelated code, comments, and formatting.

#### Creating a new file

1. Check `plan.md` for the specified path. Use it if given.
2. If no path is specified, infer placement from the surrounding project structure (e.g. a new repository class goes where other repository classes live).
3. Write the file using the conventions established in step 5.

#### Producing an artifact

A step may need to produce something that is **not** a change to the codebase — a read-only probe script, its captured output, a data extract, or a note recording what was found. These are legitimate, and for some kinds of work they are the *entire* deliverable rather than a by-product: the type file read in step 2 says which.

Follow `ticket-common/ARTIFACTS.md` for placement, naming and the run-approval rule. In outline:

1. Create `artifacts/step-{N}.{M}/` for the step being implemented, or `artifacts/shared/` when the file serves more than one step.
2. Write the script there. **Ask the user before running it** — show what it does, what it reads, and that it writes nothing outside `artifacts/`. On approval, run it and capture its output beside it.
3. If the artifacts would not explain themselves to a later reader — what was run, against what, when, and what it showed — add a `README.md` to that directory saying so.
4. Set the step's `**Artifacts:**` line in `plan.md` to the paths just created.

The approval in point 2 is required every time, for every script artifact. A plan step authorizing the *work* is not authorization to *execute* a script that step happens to produce — the plan was written before the script existed. Build commands are not script artifacts and are unaffected by this rule.

If what an artifact establishes contradicts the plan, do not quietly implement the plan anyway. Record the contradiction in the artifact, tell the user, and ask whether to revise the plan before continuing.

#### Keeping the step's status current

Set the step's `**Status:**` to `In Progress` **before making its first edit**, with a note saying the work has just begun, and keep that note current as the step's state materially changes.

Where a step cannot be completed, do not leave it reading `In Progress`:

- **Blocked on an answer** — something outside the codebase must be decided or confirmed. Set `Blocked` with a note naming what is blocking and what would clear it, tell the user, and move to the next step in the phase if one is independent of it.
- **Blocked on a contradiction** — an artifact or the codebase contradicts what the step assumes. Follow the rule under [Producing an artifact](#producing-an-artifact): record it, tell the user, and ask whether to revise the plan. Do not implement the step as written.
- **Blocked on a violated invariant** — the type file names something this kind of work must not do, and doing the step as written would do it. That is a **stop-and-report**, not a note to leave behind. Step 8 will not mark the phase done.

#### Noting decisions as they are made

Every choice made in dialogue during a phase — an approach chosen over another, a detail inferred because the plan was silent — needs to be **stated in chat with its rationale, as it happens**, and carried into the report in [step 9](#9-report-what-the-run-produced).

Saying it out loud is what preserves it. This skill does not write the session's history down; `ticket-checkpoint` does, and it builds its entry from this conversation. A decision that was made silently is one the checkpoint cannot record and the next session will re-litigate.

#### General rules

- Do not add features, abstractions, or refactors beyond what the step requires.
- Do not add comments unless the WHY is non-obvious (a hidden constraint, subtle invariant, or workaround for a specific bug).
- Do not install packages or run any shell command that modifies the codebase or environment. Read-only commands are permitted, and anything they produce is stored as an artifact — but never run a script artifact without the user's approval.

### 7. Build the affected projects

After all steps in a phase are implemented, build each project that was modified to verify the changes compile cleanly.

**Where the phase changed no source file** — because its deliverable was a written artifact — there is nothing to build. Skip this step, say so in one line, and **do not treat it as a failure or as a missing change**. The type file read in step 2 says whether that is the expected shape of the work.

Detect the build tool from the project's files:

| Signal | Build command |
| --- | --- |
| `*.sln` or `*.csproj` | `dotnet build` |
| `package.json` with a `build` script | `pnpm build` |
| `package.json` without a `build` script | `pnpm install` (dependency check only) |
| `*.tf` / `*.bicep` | skip — no compile step |
| Other | skip and note in the report |

Run the build command from the project root directory (the folder containing the solution/project file or `package.json`). If multiple projects were modified, build each one separately.

**If the build succeeds:** proceed to step 8.

**If the build fails:**

1. Read the compiler output and diagnose the error.
2. Attempt to fix the issue — it is most likely caused by the changes just made.
3. Re-run the build. If it succeeds, proceed.
4. If the build still fails after one fix attempt, stop and report the error to the user:

   > Build failed for {project} after phase {N}. Please review the compiler output below before continuing.
   >
   > {compiler output}

   Do not mark the phase complete or continue to the next phase until the build passes.

### 8. Update the phase's status in plan.md

**First, check the phase against the type's completion rule from step 2.** Where the rule is not satisfied — a required test was not run, an invariant the type protects was broken, a deliverable the type demands was not produced — the phase is **not** done. Report what is missing, set the step's status accordingly, and stop rather than continuing to the next phase.

Then, once the build passes for all affected projects:

1. Set `**Status:** Done` on every step sub-section that was actually completed. Leave a step that could not be completed as `Blocked` or `In Progress` with its note intact
2. Set the `**Artifacts:**` line of every step that produced files to the paths under `artifacts/`, relative to `plan.md`; leave it `—` for steps that produced none
3. Derive the phase row in the Progress table from its steps, using the table in `ticket-common/STATUS.md`. Add a short parenthetical where the status alone misleads — `[~] In Progress (2.7 blocked on the claim name)`
4. If all phases in the table are now `[x] Done`, update the overall summary line if present.

A phase whose steps are not all `Done` is not marked `[x] Done`, however much of it ran. The point of the derivation is that the table cannot claim more than the steps support.

Then **automatically continue** to the next selected phase (back to step 4).

---

## 9. Report what the run produced

After all selected phases are complete, report what this run actually did.

**Start with whatever the type file's *"What implement must produce"* section requires.** That section is the completion report's first obligation, and for some kinds of work it is most of it — an answer and a recommendation, a before-and-after test result, a cause that turned out to differ from the hypothesis. Do not substitute the generic report below for it.

**Where the run changed source files**, identify which projects were modified, using two signals in order:

1. **Discovered Services table in plan.md** — for each file created or edited, find the entry whose `Path` is a prefix of the modified file's path. Use the `Service` name and `Path` from that row.
2. **`.git` directory scan** — for any modified file not matched by the table above, walk up its directory tree until a `.git` directory is found. The directory containing `.git` is the project root. Use the folder name as the project name.

```
Done. Projects touched:

  • {Service name} — {relative path to project root}
```

**Where the run changed no source file**, say what it produced instead — the artifact paths, and what they establish. **Do not report an empty project list, and do not imply something is missing**; for a type whose deliverable is a written finding, that is a complete run. Check the type file before writing this sentence, not after.

Then append what this run decided and assumed, each naming the step it affects. Omit either list when it is empty:

```
Decisions:
  • {Step N.M} — {what was chosen, over what, and why}

Inferences made:
  • {Step N.M} — {what was inferred and why}
```

This report is the only place either list is written down, so state it even when it feels obvious — `ticket-checkpoint` builds the session's journal entry from this conversation, and what was never said cannot be recorded.

Close by naming where the work stands and how to keep it:

```
Left in flight: {Step N.M} — {status and its note} | Nothing in flight.
```

> Run `/ticket-checkpoint {ref}` before switching away from this ticket, and `/ticket-resume {ref}` when you come back to it.

---

## Constraints

- Always read an existing file before editing it — never overwrite it wholesale
- Only run read-only or build commands — never run commands that modify the environment, install global tools, or alter state outside the project being built
- Never implement beyond the scope of the selected phases
- Never re-implement a phase already marked `[x] Done` — warn and skip instead
- Never re-implement a step already marked `Done`, and resume rather than restart one marked `In Progress`
- **Never read or write `journal.md`** — it belongs to `ticket-checkpoint` and `ticket-resume`
- **Never read a provider file** — this skill is source-agnostic, and needing one means the abstraction leaked
- Never write a bare `In Progress` or `Blocked` status: both require a one-line note. Mark a step `In Progress` before its first edit, so an interrupted session still leaves an accurate plan
- State every decision and inference in chat with its rationale as it is made — the report is the only record of them this skill produces
- Never mark a phase `[x] Done` while any of its steps is not `Done`, or while the resolved type's completion rule is unsatisfied
- **Never report a document-only run as incomplete** where the type's deliverable is a written finding, and **never report a violated type invariant as ordinary progress** — stop and report it
- Consult `digest.md` only when `plan.md` is unclear — do not use it to expand scope beyond the plan
- Apply both local codebase conventions and the global rules in `~/.claude/rules/`; local patterns win on style, global rules win on correctness
- New file placement follows `plan.md` first, project structure second — never ask the user unless both signals are absent
- Do not run tests except where the resolved type's file requires it as its completion test; otherwise leave testing to the user
- Do not run any git operation (`commit`, `push`, `pull`, `rebase`, `merge`, `reset`, `stash`, etc.) — the developer is responsible for reviewing the diff and deciding when and how to commit
- Read a step's existing artifacts before implementing it — never re-derive what a previous run already measured
- Write every generated non-code file under `artifacts/step-{N}.{M}/` or `artifacts/shared/` — never into `artifacts/planning/`, never into the ticket root, and never into the repository being worked on
- Keep `**Artifacts:**` lines accurate: a step that produced files must name them, and a path it names must exist
- Never delete or overwrite an existing artifact — write a new file alongside it instead
- Never run a script artifact without prior authorization — write it, show it, ask, then run
- Renumber phases and steps whenever the plan's shape calls for it, and finish the rename in one pass so nothing points at an old number
