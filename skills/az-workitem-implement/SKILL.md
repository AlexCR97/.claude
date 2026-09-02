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

All `az-workitem-*` data lives under the current user's home directory, so the
paths below are the same no matter which workspace the session runs in:

```
~/.az-workitems/
```

`~` is written for brevity. Neither the file tools nor a quoted shell argument
expand it, so **resolve it to an absolute path before use** — `C:\Users\{user}`
on Windows, `/home/{user}` on Linux, `/Users/{user}` on macOS.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Locate the plan

Resolve the following against the user's home directory (see [Paths](#paths)):

- Plan path: `~/.az-workitems/{id}/plan.md`
- Digest path: `~/.az-workitems/{id}/digest.md`

If `plan.md` does not exist, stop and tell the user:

> No plan found for work item #{id}. Run `/az-workitem-plan {id}` first.

### 2. Read the plan

Parse `plan.md` and extract:

- The **Progress table** — phase names, estimates, and current status (`[ ] Pending`, `[~] In Progress`, `[x] Done`)
- Each **Phase section** — its scope, services touched, and step sub-sections (`### Step {N}.{M}`, each with a `**Status:**` and `**Target:**` line)
- The **Discovered Services table** — maps service names to relative paths and technology stack; used in step 9 to report touched projects

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

Re-read the phase section from `plan.md`. Extract each step sub-section (`### Step {N}.{M}`), its `**Status:**`, and its `**Target:**`.

If any step references a file or class that does not exist yet, note it as a **new artifact** to be created. If any step is ambiguous or underspecified:

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

#### General rules

- Do not add features, abstractions, or refactors beyond what the step requires.
- Do not add comments unless the WHY is non-obvious (a hidden constraint, subtle invariant, or workaround for a specific bug).
- Do not install packages or run any shell commands that modify the codebase or environment.

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
2. Update the phase row in the Progress table: status → `[x] Done`
3. If all phases in the table are now `[x] Done`, update the overall summary line if present.

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
