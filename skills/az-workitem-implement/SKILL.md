---
name: az-workitem-implement
description: Follow-up to az-workitem-plan. Reads plan.md for a work item and implements one, several, or all phases by making real code changes. Tracks step status (Pending, In Progress, Blocked, Done) in plan.md as it goes. On completion, reports which projects were touched and what was inferred.
---

## Input

```
/az-workitem-implement {id} [{phases}]
```

- `{id}` — required. The work item ID.
- `{phases}` — optional. One of:
  - A comma-separated list of phase numbers: `1`, `1,3`, `2,3,4`
  - The literal string `all` — runs every pending phase in order
  - Omitted — the skill shows the current progress table and prompts the user to specify

If `{id}` is not provided, ask for it before proceeding.

---

## Paths

All `az-workitem-*` data lives under the current user's home directory, so the paths below are the same no matter which workspace the session runs in:

```
~/.az-workitems/
```

`~` is written for brevity. Neither the file tools nor a quoted shell argument expand it, so **resolve it to an absolute path before use** — `C:\Users\{user}` on Windows, `/home/{user}` on Linux, `/Users/{user}` on macOS.

### Work item directory layout

```
~/.az-workitems/{id}/
├── digest.md              ← az-workitem-digest
├── journal.md             ← az-workitem-checkpoint (not this skill's — see below)
├── plan.md                ← az-workitem-plan
├── raw/                   ← az-workitem-fetch (raw.json + attachments)
└── artifacts/             ← files generated while planning or implementing
    ├── planning/          ← research az-workitem-plan did to build the plan
    ├── shared/            ← artifacts spanning more than one step
    └── step-{N}.{M}/      ← everything one plan step produced
```

`artifacts/` and its subdirectories are created lazily — only when a run actually produces a file. The work item root holds nothing but the five entries above: **never write a generated file directly into `~/.az-workitems/{id}/`.**

`journal.md` is the per-session work log, and it is **out of scope for this skill: never read it, never write to it.** It belongs to `az-workitem-checkpoint`, which writes it when attention leaves the work item, and to `az-workitem-resume`, which reads it back at the start of the next session. By the time this skill runs, `az-workitem-resume` has already loaded that history into the session, so reading it again would only spend context on what is already here. What this skill records instead is `plan.md` — the step statuses in [Step Status](#step-status) — and the chat report in [step 9](#9-report-touched-projects).

**Placement rules**

- A file belongs to the step that produced it: `artifacts/step-{N}.{M}/`, where `{N}.{M}` matches the `### Step {N}.{M}` heading in `plan.md` exactly.
- A file that more than one step reads, or that applies to the plan as a whole (a findings document, a data extract several steps consult), goes in `artifacts/shared/`.
- `artifacts/planning/` belongs to `az-workitem-plan` — read it, never write to it. It holds the research the plan was built on, so an artifact there explains *why* a step is shaped the way it is.
- The captured output of running a script is written beside it as `{name}.output.{ext}`, where `{ext}` is the format the output actually is — `.json` for a JSON document, `.csv`, `.tsv`, `.jsonl`, `.md`, `.sql`, `.xml`, and so on. **Default to `.txt`**, and reach for a structured extension only when the whole file parses as that format: console output that mixes a table, a log line and a summary is `.txt`, however much JSON it happens to contain. Naming a capture for what it holds is what lets a later run parse it instead of re-running the script to get the data in a usable shape.
- When a structured capture would be spoiled by diagnostics, keep stdout in the structured file and put stderr beside it as `{name}.stderr.txt`. Where output is plain text anyway, one combined `{name}.output.txt` is simpler and preferred.
- Any of these directories may hold a `README.md` recording what was done and what it found. Write one whenever the artifacts alone would not tell a later reader why they exist.

**Renumbering**

Plans change shape: research reorders phases, one step splits into two, a phase turns out to belong earlier. **Renumber whenever the plan reads better for it.** A step number is also a directory name, though, so renumbering is a rename — and it is finished only when nothing still points at the old number:

1. Rename each affected `artifacts/step-{old}/` to `artifacts/step-{new}/`.
2. Update the `## Phase {N}` and `### Step {N}.{M}` headings in `plan.md`.
3. Update every `**Artifacts:**` line that named a renamed directory.
4. Search `plan.md` and every file under `artifacts/` — `planning/`, `shared/`, and each step's `README.md` included — for the old identifiers (`step-1.1`, `Step 1.1`, `Phase 3`) and update each occurrence.
5. Tell the user what moved and why.

Do all five in one pass. A half-renumbered plan, where an `**Artifacts:**` line points at a directory that no longer exists, is worse than one that was never renumbered at all.

Nothing here belongs in the repository being worked on. A artifact is a record of how this work item was investigated, not a deliverable — never copy one into the codebase unless a plan step explicitly says to.

---

## Step Status

A step's `**Status:**` line takes exactly one of four values, optionally followed by ` — ` and a one-line note:

| Status        | Means                 | Note                                                                    |
| ------------- | --------------------- | ----------------------------------------------------------------------- |
| `Pending`     | Not started           | None                                                                    |
| `In Progress` | Started, not finished | **Required** — what is done and what remains                            |
| `Blocked`     | Cannot proceed        | **Required** — what is blocking, and what would clear it                |
| `Done`        | Finished              | Optional — only where the outcome differed from what the step asked for |

e.g.:

```
**Status:** In Progress — harness runs for the Analytics job; the Identity case throws at startup
**Status:** Blocked — waiting on the Identity team to confirm the claim name
```

`In Progress` and `Blocked` exist so that stopping mid-phase is recordable. A session that ends between steps must leave the plan saying so: a step that is 80% finished marked `Pending` loses the 80%, and marked `Done` loses far more than that. The note is what makes the state actionable later — `In Progress` alone says only that a step was touched.

The phase's row in the Progress table is **derived** from its steps, never set independently:

| Condition                        | Phase status      |
| -------------------------------- | ----------------- |
| Any step `Blocked`               | `[!] Blocked`     |
| Every step `Done`                | `[x] Done`        |
| Any step `Done` or `In Progress` | `[~] In Progress` |
| Otherwise                        | `[ ] Pending`     |

A phase row may carry a short parenthetical where the count alone misleads — `[x] Done (4 skipped)`, `[~] In Progress (2.7 left to run)`.

The note is the whole of what this skill records about *why* a step is where it is, so make it carry its weight in one line. The fuller account of a session — decisions, rationale, the next action — is `az-workitem-checkpoint`'s to write, from this session's conversation, when attention leaves the work item.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Locate the plan

Resolve the following against the user's home directory (see [Paths](#paths)):

- Plan path: `~/.az-workitems/{id}/plan.md`
- Digest path: `~/.az-workitems/{id}/digest.md`
- Artifacts directory: `~/.az-workitems/{id}/artifacts/` — may not exist yet

If `plan.md` does not exist, stop and tell the user:

> No plan found for work item #{id}. Run `/az-workitem-plan {id}` first.

### 2. Read the plan

Parse `plan.md` and extract:

- The **Progress table** — phase names, estimates, and current status (`[ ] Pending`, `[~] In Progress`, `[!] Blocked`, `[x] Done`)
- Each **Phase section** — its scope, services touched, and step sub-sections (`### Step {N}.{M}`, each with a `**Status:**`, `**Target:**`, and `**Artifacts:**` line). A `**Status:**` line may carry a note after an em dash; see [Step status](#step-status)
- The **Discovered Services table** — maps service names to relative paths and technology stack; used in step 9 to report touched projects

Then list `~/.az-workitems/{id}/artifacts/`. Every `**Artifacts:**` line that names a directory should have one on disk, and every directory on disk should be named by some step's `**Artifacts:**` line. Where they disagree, trust the disk and correct `plan.md`.

A step marked `In Progress` or `Blocked` was left mid-flight by an earlier session. Its `**Status:**` note is what this skill goes on, together with anything about that session already in this conversation — `az-workitem-resume` puts it there when it briefs the session. Do not open `journal.md` to look for more.

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

A step may need to produce something that is **not** a change to the codebase — a read-only probe script, its captured output, a data extract, or a note recording what was found. These are legitimate, and often the most valuable output a step has. Store them under the layout in [Paths](#paths):

1. Create `artifacts/step-{N}.{M}/` for the step being implemented, or `artifacts/shared/` when the file serves more than one step.
2. Write the script there. **Ask the user before running it** — show what it does, what it reads, and that it writes nothing outside `artifacts/`. On approval, run it and capture its output beside it as `{name}.output.{ext}`, the extension naming the format the output actually is and defaulting to `.txt` (see [Paths](#paths)).
3. If the artifacts would not explain themselves to a later reader — what was run, against what, when, and what it showed — add a `README.md` to that directory saying so.
4. Set the step's `**Artifacts:**` line in `plan.md` to the paths just created.

Scripts written this way must be **read-only** with respect to any external system they touch. A probe that reads a production database is in scope; anything that writes to one is a change to the environment and is not.

The approval in point 2 is required every time, for every script artifact. A plan step authorizing the *work* is not authorization to *execute* a script that step happens to produce — the plan was written before the script existed. Build commands (`dotnet build`, `pnpm build`) are not script artifacts and are unaffected by this rule.

If what an artifact establishes contradicts the plan, do not quietly implement the plan anyway. Record the contradiction in the artifact, tell the user, and ask whether to revise the plan before continuing.

#### Keeping the step's status current

Set the step's `**Status:**` to `In Progress` **before making its first edit**, with a note saying the work has just begun, and keep that note current as the step's state materially changes. A session can end at any moment — an interrupt, a context switch, a closed terminal — and only what is already on disk survives it. A status written after the fact is a status that is sometimes never written at all.

Where a step cannot be completed, do not leave it reading `In Progress`:

- **Blocked on an answer** — something outside the codebase must be decided or confirmed. Set `Blocked` with a note naming what is blocking and what would clear it, tell the user, and move to the next step in the phase if one is independent of it.
- **Blocked on a contradiction** — an artifact or the codebase contradicts what the step assumes. Follow the rule under [Producing an artifact](#producing-an-artifact): record it, tell the user, and ask whether to revise the plan. Do not implement the step as written.

#### Noting decisions as they are made

Every choice made in dialogue during a phase — an approach chosen over another, a detail inferred because the plan was silent — needs to be **stated in chat with its rationale, as it happens**, and carried into the report in [step 9](#9-report-touched-projects).

Saying it out loud is what preserves it. This skill does not write the session's history down; `az-workitem-checkpoint` does, and it builds its entry from this conversation. A decision that was made silently is one the checkpoint cannot record and the next session will re-litigate.

#### General rules

- Do not add features, abstractions, or refactors beyond what the step requires.
- Do not add comments unless the WHY is non-obvious (a hidden constraint, subtle invariant, or workaround for a specific bug).
- Do not install packages or run any shell command that modifies the codebase or environment. Read-only commands are permitted, and anything they produce is stored as an artifact (above) — but never run a script artifact without the user's approval.

### 7. Build the affected projects

After all steps in a phase are implemented, build each project that was modified to verify the changes compile cleanly.

Detect the build tool from the project's files:

| Signal                                  | Build command                          |
| --------------------------------------- | -------------------------------------- |
| `*.sln` or `*.csproj`                   | `dotnet build`                         |
| `package.json` with a `build` script    | `pnpm build`                           |
| `package.json` without a `build` script | `pnpm install` (dependency check only) |
| `*.tf` / `*.bicep`                      | skip — no compile step                 |
| Other                                   | skip and note in the report            |

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

After the build passes for all affected projects:

1. Set `**Status:** Done` on every step sub-section that was actually completed. Leave a step that could not be completed as `Blocked` or `In Progress` with its note intact — see [Step Status](#step-status)
2. Set the `**Artifacts:**` line of every step that produced files to the paths under `artifacts/`, relative to `plan.md`; leave it `—` for steps that produced none
3. Derive the phase row in the Progress table from its steps, using the table in [Step Status](#step-status). Add a short parenthetical where the status alone misleads — `[~] In Progress (2.7 blocked on the claim name)`
4. If all phases in the table are now `[x] Done`, update the overall summary line if present.

A phase whose steps are not all `Done` is not marked `[x] Done`, however much of it ran. The point of the derivation is that the table cannot claim more than the steps support.

Then **automatically continue** to the next selected phase (back to step 4).

---

## 9. Report touched projects

After all selected phases are complete, identify which projects were actually modified during this run.

Use two signals, in order:

1. **Discovered Services table in plan.md** — for each file created or edited, find the entry in the Discovered Services table whose `Path` is a prefix of the modified file's path. Use the `Service` name and `Path` from that row.

2. **`.git` directory scan** — for any modified file not matched by the table above, walk up its directory tree until a `.git` directory is found. The directory containing `.git` is the project root. Use the folder name as the project name.

Print the touched projects as the completion message — one line per project:

```
Done. Projects touched:

  • {Service name} — {relative path to project root}
  • {Service name} — {relative path to project root}
```

Then append what this run decided and assumed, each naming the step it affects. Omit either list when it is empty:

```
Decisions:
  • {Step N.M} — {what was chosen, over what, and why}

Inferences made:
  • {Step N.M} — {what was inferred and why}
```

This report is the only place either list is written down, so state it even when it feels obvious — `az-workitem-checkpoint` builds the session's journal entry from this conversation, and what was never said cannot be recorded.

Close by naming where the work stands and how to keep it:

```
Left in flight: {Step N.M} — {status and its note} | Nothing in flight.
```

> Run `/az-workitem-checkpoint {id}` before switching away from this work item, and `/az-workitem-resume {id}` when you come back to it.

---

## Constraints

- Always read an existing file before editing it — never overwrite it wholesale
- Only run read-only or build commands (`dotnet build`, `pnpm build`, etc.) — never run commands that modify the environment, install global tools, or alter state outside the project being built
- Never implement beyond the scope of the selected phases
- Never re-implement a phase already marked `[x] Done` — warn and skip instead
- Never re-implement a step already marked `Done`, and resume rather than restart one marked `In Progress`
- **Never read or write `journal.md`** — it belongs to `az-workitem-checkpoint` and `az-workitem-resume`. Resume has already brought its contents into the session; reading it again only spends context on what is already here
- Never write a bare `In Progress` or `Blocked` status: both require a one-line note. Mark a step `In Progress` before its first edit, so an interrupted session still leaves an accurate plan
- State every decision and inference in chat with its rationale as it is made — the report is the only record of them this skill produces
- Never mark a phase `[x] Done` while any of its steps is not `Done` — the phase row is always derived from its steps
- Consult `digest.md` only when `plan.md` is unclear — do not use it to expand scope beyond the plan
- Apply both local codebase conventions and the global rules in `~/.claude/rules/`; local patterns win on style, global rules win on correctness
- New file placement follows `plan.md` first, project structure second — never ask the user unless both signals are absent
- Do not run tests — leave that to the user
- Do not run any git operation (`commit`, `push`, `pull`, `rebase`, `merge`, `reset`, `stash`, etc.) — the developer is responsible for reviewing the diff and deciding when and how to commit
- Read a step's existing artifacts before implementing it — never re-derive what a previous run already measured
- Write every generated non-code file under `artifacts/step-{N}.{M}/` or `artifacts/shared/` — never into `artifacts/planning/` (which belongs to `az-workitem-plan`), never into the work item root, and never into the repository being worked on
- Keep `**Artifacts:**` lines accurate: a step that produced files must name them, and a path it names must exist
- Never delete or overwrite an existing artifact — a measurement taken against a live system is the one thing here that cannot be regenerated. Write a new file alongside it instead. Renaming a step directory during a renumbering pass is not a deletion, and is expected
- Never run a script artifact without prior authorization — write it, show it, ask, then run
- Renumber phases and steps whenever the plan's shape calls for it, and finish the rename in one pass (see [Paths](#paths)) so nothing points at an old number
