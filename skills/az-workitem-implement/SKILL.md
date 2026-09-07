---
name: az-workitem-implement
description: Follow-up to az-workitem-plan. Reads plan.md for a work item and implements one, several, or all phases by making real code changes. Marks phases complete in plan.md as it goes. On completion, reports which projects were touched.
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
├── plan.md                ← az-workitem-plan
├── raw/                   ← az-workitem-fetch (raw.json + attachments)
└── artifacts/             ← files generated while planning or implementing
    ├── planning/          ← research az-workitem-plan did to build the plan
    ├── shared/            ← artifacts spanning more than one step
    └── step-{N}.{M}/      ← everything one plan step produced
```

`artifacts/` and its subdirectories are created lazily — only when a run actually produces a file. The work item root holds nothing but the four entries above: **never write a generated file directly into `~/.az-workitems/{id}/`.**

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

- The **Progress table** — phase names, estimates, and current status (`[ ] Pending`, `[~] In Progress`, `[x] Done`)
- Each **Phase section** — its scope, services touched, and step sub-sections (`### Step {N}.{M}`, each with a `**Status:**`, `**Target:**`, and `**Artifacts:**` line)
- The **Discovered Services table** — maps service names to relative paths and technology stack; used in step 9 to report touched projects

Then list `~/.az-workitems/{id}/artifacts/`. Every `**Artifacts:**` line that names a directory should have one on disk, and every directory on disk should be named by some step's `**Artifacts:**` line. Where they disagree, trust the disk and correct `plan.md`.

### 3. Resolve which phases to implement

If `{phases}` was provided as `all`, collect every phase whose status is not `[x] Done`.

If `{phases}` was provided as a comma-separated list, collect those phase numbers — but **skip any that are already `[x] Done`** and warn the user for each skipped one:

> Phase {N} ({name}) is already marked done — skipping.

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

### 8. Mark the phase complete in plan.md

After the build passes for all affected projects:

1. Set `**Status:** Done` on every step sub-section in the phase section
2. Set the `**Artifacts:**` line of every step that produced files to the paths under `artifacts/`, relative to `plan.md`; leave it `—` for steps that produced none
3. Update the phase row in the Progress table: status → `[x] Done`
4. If all phases in the table are now `[x] Done`, update the overall summary line if present.

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

If any steps were implemented using inferred details (because the plan was underspecified), append a note:

```
Inferences made:
  • {step description} — {what was inferred and why}
```

---

## Constraints

- Always read an existing file before editing it — never overwrite it wholesale
- Only run read-only or build commands (`dotnet build`, `pnpm build`, etc.) — never run commands that modify the environment, install global tools, or alter state outside the project being built
- Never implement beyond the scope of the selected phases
- Never re-implement a phase already marked `[x] Done` — warn and skip instead
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
