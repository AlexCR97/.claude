---
name: ticket-implement
description: Implements one, several or all phases of a ticket's plan.md by making the code changes each step names, then builds the affected projects. Tracks step status in plan.md as it goes, and reports what the run produced, decided and inferred.
argument-hint: "<ref> [phases | all]"
---

Implements one, several or all phases of a ticket's `plan.md`: makes the code changes each step names, in the worktrees the plan's Workspace section confirms, builds each affected project, and keeps every step's status in `plan.md` current as it goes. What this run has to show before a phase is done — and whether a phase with no code change is complete — comes from the ticket's type.

End state: each selected phase's steps done and marked `Done`, or stopped with an accurate status and note; the affected projects building; `plan.md` and `artifacts/` matching what the run produced; no git operation run; and a report of what the run produced, decided and inferred.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                              |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | **none.** See below               |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

No `allowed-tools` here: this skill's whole purpose is to change code and build it, so an allowlist would be theatre.

---

## Parameters

- **`<ref>`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Ask for one when it is absent.
- **`[phases | all]`** — a comma-separated list of phase numbers (`1`, `1,3`, `2,3,4`), or `all` for every phase not yet done, in order. Absent, Step 3 shows the progress table and asks.

---

## Ground rules

1. **Stay inside the selected phases.** Never implement beyond them, and never use `digest.md` to expand scope beyond the plan.
2. **Never redo finished work.** Skip a phase marked `[x] Done` or a step marked `Done`, with a warning; resume a step marked `In Progress` rather than restarting it.
3. **Run only read-only and build commands.** Never install a package or global tool, change the environment, or alter state outside the project being built. Run tests only where the type's file makes them its completion test.
4. **Never run a git operation** — commit, push, pull, rebase, merge, reset, stash or any other. The developer reviews the diff and decides when to commit.
5. **Never run a script artifact without approval of that run.** Write it, show it, ask, then run.
6. **Never read or write `journal.md`.** It belongs to `ticket-checkpoint` and `ticket-resume`, and `ticket-resume` has already brought what matters into the session.
7. **Never read a provider file.** By now `digest.md` holds what the ticket said and `plan.md` what the work is; needing a provider file means the abstraction leaked — report it as a bug.
8. **Keep `plan.md` honest.** Mark a step `In Progress` before its first edit — only what is on disk survives an interrupted session. Never write a bare `In Progress` or `Blocked` status, keep every `**Artifacts:**` line accurate, and never mark a phase `[x] Done` while a step is not `Done`. `ticket-common/STATUS.md` has the vocabulary and the note rules.
9. **Write non-code files only under `artifacts/step-{N}.{M}/` or `artifacts/shared/`.** Never into `artifacts/planning/`, which belongs to `ticket-plan`, the ticket directory or the workspace; never delete or overwrite an existing artifact. `ticket-common/ARTIFACTS.md` has the layout.
10. **State every decision and inference in chat as it is made.** The report is the only record this skill produces, and `ticket-checkpoint` builds its entry from the conversation.
11. **Honour the type's completion rule both ways.** Never report a document-only run as incomplete where the type's deliverable is a written finding, and never report a violated type invariant as progress — stop and report it.
12. **Renumber in one pass.** When the plan's shape changes, finish the rename so nothing points at an old number — `ticket-common/ARTIFACTS.md` → *Renumbering is a rename*.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require plan [--context {context}]
```

Everything below uses the paths and type it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `plan` requirement means there is nothing to implement; the hint names the skill that fixes it.

### Step 2 — Read the type's completion rule, then the plan

Read `ticket-types/{type}.md`, specifically its *"What done means"* and *"What implement must produce"* sections. They define what this run has to show for itself before any phase may be reported complete, and they are the only thing that varies here by type. Take them seriously in both directions: a type whose deliverable is a document is not an incomplete run, and a type whose invariant was broken is not a run that merely needs a note.

Then parse `plan.md` and extract:

- The **Progress table** — phase names, estimates, and current status (`[ ] Pending`, `[~] In Progress`, `[!] Blocked`, `[x] Done`)
- Each **Phase section** — its scope, projects touched, and step sub-sections (`### Step {N}.{M}`, each with a `**Status:**`, `**Target:**`, and `**Artifacts:**` line)
- The **Workspace section** — each worktree and plain directory, by absolute path, and the projects inside them; used in Steps 6 and 9

The terms in that section, and throughout this skill, mean exactly what **`ticket-common/GLOSSARY.md`** says. The workspace is where this run works: never read or change a worktree it does not list, even one of a repository it holds, and never rediscover it.

Then list the ticket's `artifacts/`. Every `**Artifacts:**` line that names a directory should have one on disk, and every directory on disk should be named by some step's `**Artifacts:**` line. Where they disagree, trust the disk and correct `plan.md`.

A step marked `In Progress` or `Blocked` was left mid-flight by an earlier session. Its `**Status:**` note is what this skill goes on, together with anything about that session already in this conversation — `ticket-resume` puts it there when it briefs the session. Do not open `journal.md` to look for more.

### Step 3 — Resolve which phases to implement

- **`all`** → collect every phase whose status is not `[x] Done`.
- **A list of phase numbers** → collect those phases, but skip any that are already `[x] Done`, and warn the user for each skipped one, naming the phase.
- **Absent** → print the current progress table and ask:

  > Which phases would you like to implement? Enter phase numbers separated by commas, or "all" for all pending phases.

  Wait for the response, then resolve as above.

A phase whose status is `[!] Blocked` is **not** skipped automatically, but it is not run silently either. Report the blocking step and its note, and ask whether it has been resolved — offering to implement the phase's other steps, or to wait. Implementing straight through a blocker usually produces work that has to be redone once the real answer arrives.

- **Resolved** → implement the phase, starting at the blocked step.
- **The other steps** → implement every step of the phase except the blocked one, which stays `Blocked`.
- **Wait** → leave the phase out of this run.

A phase holding an `In Progress` step resumes at that step rather than restarting the phase — its `**Status:**` note says what is already done.

If no phases remain after filtering out done ones, stop:

> All specified phases are already complete. Nothing to implement.

### Step 4 — Read the phase steps

Run Steps 4–8 once for each resolved phase, in ascending order.

Re-read the phase section from `plan.md`. Extract each step sub-section (`### Step {N}.{M}`), its `**Status:**`, `**Target:**`, and `**Artifacts:**`.

Skip any step already marked `Done`. Resume — do not restart — any step marked `In Progress`: read its `**Status:**` note first and take what it says was already done as done. Re-doing a completed half of a step is how a resumed session quietly reverts a decision the previous one made.

For every step whose `**Artifacts:**` line is not `—`, read that step's artifacts directory before implementing anything. A previous run left those files there because they carry something the plan alone does not: a measurement, a query result, an extract, a correction. Treat what they establish as fact, and never re-run a probe whose output is already on disk. Also read `artifacts/shared/` and `artifacts/planning/` if they exist — a findings document in either may carry the premise the step was built on, or a later correction to it.

If any step references a file or class that does not exist yet, note it as a new file to be created. If any step is ambiguous or underspecified:

1. First consult `digest.md` — the **Acceptance Criteria**, **Description**, and **Discussion** sections often resolve ambiguity.
2. If still unclear, use best judgment based on the patterns already established in the relevant project. Record what was inferred — it will be included in the completion report.

### Step 5 — Load coding standards

Before writing any code, `Glob` `../../rules/*.md` and read each file that applies to the projects being modified — the conventions for their language, and the language-neutral ones. They apply unless a local convention overrides them.

For each project being modified, also read enough of the existing code to identify:

- Naming conventions in use (file names, class names, method names)
- Directory structure and where new files of each type belong
- Patterns already established (e.g. how repositories are structured, how DTOs are named)

The project's own patterns take precedence over global rules where they differ, **except** where the global rules explicitly prohibit a pattern (e.g. blocking async void, enforcing `private readonly` dependencies).

### Step 6 — Implement the steps

Work through each step in the phase sequentially. For every step:

A `**Target:**` path is relative to its project's worktree or plain directory, named after the path where the workspace holds more than one. Resolve it against the absolute path the Workspace section records for that worktree or plain directory, never against the invocation directory.

#### Modifying an existing file

1. Read the file in full before making any change.
2. Make targeted edits — never replace the entire file content.
3. Preserve all unrelated code, comments, and formatting.

#### Creating a new file

1. Check `plan.md` for the specified path. Use it if given.
2. If no path is specified, infer placement from the project's directory structure (e.g. a new repository class goes where other repository classes live). Ask the user only when both signals are absent.
3. Write the file using the conventions established in Step 5.

#### Producing an artifact

A step may need to produce something that is **not** a change to the workspace — a read-only probe script, its captured output, a data extract, or a note recording what was found. These are legitimate, and for some kinds of work they are the *entire* deliverable rather than a by-product: the type file read in Step 2 says which.

Follow `ticket-common/ARTIFACTS.md` for placement, naming and the run-approval rule. In outline:

1. Create `artifacts/step-{N}.{M}/` for the step being implemented, or `artifacts/shared/` when the file serves more than one step.
2. Write the script there. Ask the user before running it — show what it does, what it reads, and that it writes nothing outside `artifacts/`. On approval, run it and capture its output beside it.
3. If the artifacts would not explain themselves to a later reader — what was run, against what, when, and what it showed — add a `README.md` to that directory saying so.
4. Set the step's `**Artifacts:**` line in `plan.md` to the paths just created.

The approval in point 2 is required for every run of every script artifact, and a contradicting artifact stops the step — both per `ticket-common/ARTIFACTS.md` → *Running a script is always a separate permission*.

#### Keeping the step's status current

Set the step's `**Status:**` to `In Progress` before making its first edit, with a note saying the work has just begun, and keep that note current as the step's state materially changes.

Where a step cannot be completed, do not leave it reading `In Progress`:

- **Blocked on an answer** — something outside the workspace must be decided or confirmed. Set `Blocked` with a note naming what is blocking and what would clear it, tell the user, and move to the next step in the phase if one is independent of it.
- **Blocked on a contradiction** — an artifact or the workspace contradicts what the step assumes. Follow `ticket-common/ARTIFACTS.md`: record it, tell the user, and ask whether to revise the plan. Do not implement the step as written.
- **Blocked on a violated invariant** — the type file names something this kind of work must not do, and doing the step as written would do it. That is a **stop-and-report**, not a note to leave behind. Step 8 will not mark the phase done.

#### Noting decisions as they are made

Every choice made in dialogue during a phase — an approach chosen over another, a detail inferred because the plan was silent — needs to be stated in chat with its rationale, as it happens, and carried into the report in Step 9.

Saying it out loud is what preserves it. This skill does not write the session's history down; `ticket-checkpoint` does, and it builds its entry from this conversation. A decision that was made silently is one the checkpoint cannot record and the next session will re-litigate.

#### General rules

- Do not add features, abstractions, or refactors beyond what the step requires.
- Do not add comments unless the WHY is non-obvious (a hidden constraint, subtle invariant, or workaround for a specific bug).
- Do not install packages or run any shell command that modifies the workspace or environment. Read-only commands are permitted, and anything they produce is stored as an artifact — but never run a script artifact without the user's approval.

### Step 7 — Build the affected projects

After all steps in a phase are implemented, build each project that was modified to verify the changes compile cleanly. Do not run tests unless the type's file makes them its completion test.

**Where the phase changed no source file** — because its deliverable was a written artifact — there is nothing to build. Skip this step, say so in one line, and do not treat it as a failure or as a missing change. The type file read in Step 2 says whether that is the expected shape of the work.

Detect the build tool from the project's files, per [`BUILD-COMMANDS.md`](./BUILD-COMMANDS.md). Run the build command from the project's directory (the one holding its solution file, project file or `package.json`). If multiple projects were modified, build each one separately.

**If the build succeeds:** proceed to Step 8.

**If the build fails:**

1. Read the compiler output and diagnose the error.
2. Attempt to fix the issue — it is most likely caused by the changes just made.
3. Re-run the build. If it succeeds, proceed.
4. If the build still fails after one fix attempt, stop: report which project failed after which phase, with the compiler output, and ask the user to review it before continuing. Do not mark the phase complete or continue to the next phase until the build passes.

### Step 8 — Update the phase's status in plan.md

First, check the phase against the type's completion rule from Step 2. Where the rule is not satisfied — a required test was not run, an invariant the type protects was broken, a deliverable the type demands was not produced — the phase is **not** done. Report what is missing, set the step's status accordingly, and stop rather than continuing to the next phase.

Then, once the build passes for all affected projects:

1. Set `**Status:** Done` on every step sub-section that was actually completed. Leave a step that could not be completed as `Blocked` or `In Progress` with its note intact
2. Set the `**Artifacts:**` line of every step that produced files to the paths under `artifacts/`, relative to `plan.md`; leave it `—` for steps that produced none
3. Derive the phase row in the Progress table from its steps, using the table in `ticket-common/STATUS.md`. Add a short parenthetical where the status alone misleads — `[~] In Progress (2.7 blocked on the claim name)`
4. If all phases in the table are now `[x] Done`, update the overall summary line if present.

A phase whose steps are not all `Done` is not marked `[x] Done`, however much of it ran. The point of the derivation is that the table cannot claim more than the steps support.

Then continue with the next selected phase at Step 4 — do not ask. After the last one, continue to Step 9.

### Step 9 — Report what the run produced

After all selected phases are complete, report what this run actually did.

Start with whatever the type file's *"What implement must produce"* section requires. That section is the completion report's first obligation, and for some kinds of work it is most of it — an answer and a recommendation, a before-and-after test result, a cause that turned out to differ from the hypothesis. Do not substitute the generic report below for it.

**Where the run changed source files**, identify which projects were modified, using two signals in order:

1. **The Workspace section's Projects table** — for each file created or edited, find the row whose directory holds it: the absolute path of the worktree or plain directory it lives in, joined with its `Path`. Use that row's project name.
2. **The file's worktree** — for a modified file no project row holds, walk up from it to the directory holding a `.git` entry: a directory in a main worktree, a file in a linked one. That directory is the worktree; report it, referred to as the glossary says, in place of a project.

**Where the run changed no source file**, say what it produced instead — the artifact paths, and what they establish. Do not report an empty project list, and do not imply something is missing; for a type whose deliverable is a written finding, that is a complete run. Check the type file before writing this sentence, not after.

Then report what this run decided and assumed, each naming the step it affects. This report is the only place either list is written down, so state it even when it feels obvious — `ticket-checkpoint` builds the session's journal entry from this conversation, and what was never said cannot be recorded.

Fill [`run-report.md`](./run-report.md): `{location}` is the worktree or plain directory, named as the glossary says, and `{filePath}` is relative to it. Omit Decisions or Inferences when it is empty. `Left in flight` reads `Nothing in flight.` when no step is left mid-way.
