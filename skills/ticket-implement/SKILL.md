---
name: ticket-implement
description: Implements one, several or all phases of a ticket's plan by making the code changes each step names, then builds the affected projects. Tracks step status in the phase files as it goes, checks each phase's dependencies and prerequisites first, and reports what the run produced, decided and inferred.
argument-hint: "<ref> [phases | all]"
---

Implements one, several or all phases of a ticket's plan: makes the code changes each step names, in the worktrees the plan's Workspace section confirms, builds each affected project, and keeps every step's status in its phase file current as it goes. The plan's graph says which phases are Ready; several sessions can each take one and run side by side, so this skill checks a phase's dependencies, prerequisites and status before starting it, and never mistakes another session's half-finished work for its own. What this run has to show before a phase is done — and whether a phase with no code change is complete — comes from the ticket's type.

End state: each selected phase's steps done and marked `Done`, or stopped with an accurate status and note; the affected projects building; the phase files, the generated block in `plan/plan.md` and `artifacts/` matching what the run produced; no git operation run; and a report of what the run produced, decided and inferred.

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
- **`[phases | all]`** — a comma-separated list of phase numbers (`1`, `1,3`, `2,3,4`), or `all` for every phase not yet done. Either way they run one after another in this session, in number order — which is dependency order, so each runs after what it depends on. Absent, Step 3 shows the Progress table and asks.

---

## Ground rules

1. **Stay inside the selected phases.** Never implement beyond them, and never use `digest.md` to expand scope beyond the plan.
2. **Never redo finished work, and never take over another session's.** Skip a `Done` phase or step, with a warning. A phase already `In Progress` when this run reaches it may belong to another session: ask before resuming it, then resume its in-flight step rather than restarting it.
3. **Run only read-only and build commands.** Never install a package or global tool, change the environment, or alter state outside the project being built. Run tests only where the type's file makes them its completion test.
4. **Never run a git operation** — commit, push, pull, rebase, merge, reset, stash or any other. The developer reviews the diff and decides when to commit.
5. **Never run a script artifact without approval of that run.** Write it, show it, ask, then run.
6. **Never read or write `journal.md`.** It belongs to `ticket-checkpoint` and `ticket-resume`, and `ticket-resume` has already brought what matters into the session.
7. **Never read a provider file.** By now `digest.md` holds what the ticket said and the plan what the work is; needing a provider file means the abstraction leaked — report it as a bug.
8. **Keep the plan honest.** Mark a step `In Progress` in its phase file before its first edit — only what is on disk survives an interrupted session. Never write a bare `In Progress` or `Blocked` status, keep every `**Artifacts:**` line accurate, and run `ticket.py plan-sync` after every status change. Never edit the generated block in `plan.md`, and never edit the phase file of a phase this run did not select. `ticket-common/STATUS.md` has the vocabulary and the note rules.
9. **Write non-code files only under `artifacts/step-{N}.{M}/` or `artifacts/shared/`.** Never into `artifacts/planning/`, which belongs to `ticket-plan`, the ticket directory or the workspace; never delete or overwrite an existing artifact. `ticket-common/ARTIFACTS.md` has the layout.
10. **State every decision and inference in chat as it is made.** The report is the only record this skill produces, and `ticket-checkpoint` builds its entry from the conversation.
11. **Honour the type's completion rule both ways.** Never report a document-only run as incomplete where the type's deliverable is a written finding, and never report a violated type invariant as progress — stop and report it.
12. **Never fix what this phase did not touch.** A build error in a file outside this phase's changes is most likely another session's work in flight; report it rather than editing it.
13. **Never renumber.** Renumbering renames artifact directories other sessions may be writing into; only `ticket-plan` does it. Where the plan's shape needs to change, say so and point at `/ticket-plan`.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require plan [--context {context}]
```

Everything below uses the paths and type it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `plan` requirement means there is nothing to implement, or that the plan is in an old format; the hint names the skill that fixes it.

### Step 2 — Read the type's completion rule, then the plan

Read `ticket-types/{type}.md`, specifically its *"What done means"* and *"What implement must produce"* sections. They define what this run has to show for itself before any phase may be reported complete, and they are the only thing that varies here by type. Take them seriously in both directions: a type whose deliverable is a document is not an incomplete run, and a type whose invariant was broken is not a run that merely needs a note.

Then sync the plan and read what it reports:

```bash
python "{skills}/ticket-common/ticket.py" plan-sync "<ref>" [--context {context}]
```

Its output lists every phase — number, title, file, `depends_on`, derived status, whether it is Ready and why not, its open prerequisites, and each step's status, note and target. Another session may have changed a phase file since this one last looked, so this is the plan's current state, and the run trusts it over anything remembered.

Read the **Workspace section** of `plan.md` — each worktree and plain directory, by absolute path, and the projects inside them; used in Steps 6 and 9. The terms in that section, and throughout this skill, mean exactly what **`ticket-common/GLOSSARY.md`** says. The workspace is where this run works: never read or change a worktree it does not list, even one of a repository it holds, and never rediscover it.

A step marked `In Progress` or `Blocked` was left mid-flight — by an earlier session, or by one still running. Its `**Status:**` note is what this skill goes on, together with anything about that session already in this conversation — `ticket-resume` puts it there when it briefs the session. Do not open `journal.md` to look for more.

### Step 3 — Resolve which phases to implement

- **`all`** → collect every phase whose status is not `[x] Done`, in number order.
- **A list of phase numbers** → collect those phases in number order, but skip any that are already `[x] Done`, and warn the user for each skipped one, naming the phase.
- **Absent** → print the Progress table from the sync — with its Depends on and Ready columns — name the Ready phases not yet started, and ask:

  > Which phases would you like to implement? Enter phase numbers separated by commas, or "all" for every phase not done. Ready phases can each run in a session of its own, in parallel with this one.

  Wait for the response, then resolve as above.

If no phases remain after filtering out done ones, stop:

> All specified phases are already complete. Nothing to implement.

### Step 4 — Check the phase can start

Run Steps 4–8 once for each resolved phase, in number order. Before touching anything, re-run `plan-sync` and check the phase against what it reports now — a phase earlier in this run may have just finished, and another session may have moved since Step 2.

- **A dependency is not `Done`** → name each phase it depends on that is not, with its status, and ask whether to go ahead anyway — the developer may know it is finished elsewhere — or leave the phase out of this run. Building on an unfinished dependency usually means redoing the work once it lands.
- **The phase is `In Progress`** → it may belong to another session. Say so, with the in-flight step's note — "Phase 3 is In Progress (Step 3.2 — repository written, mapping remains); another session may own it. Resume here?" — and wait. On a yes, resume at that step; otherwise leave the phase out.
- **The phase is `Blocked`** → report the blocking step and its note, and ask whether it has been resolved — offering to implement the phase's other steps, or to wait. Implementing straight through a blocker usually produces work that has to be redone once the real answer arrives.
  - **Resolved** → implement the phase, starting at the blocked step.
  - **The other steps** → implement every step of the phase except the blocked one, which stays `Blocked`.
  - **Wait** → leave the phase out of this run.
- **A prerequisite is unchecked** → list each one in the phase's `## Prerequisites`, and ask whether it is in place. Check the box, `- [x]`, for each the user confirms, then sync. Where one is not in place, the phase is not Ready: leave it out, unless the user chooses to go ahead.

A phase left out is named in the report, with why.

### Step 5 — Read the phase steps

Re-read the phase file. Extract each step sub-section (`### Step {N}.{M}`), its `**Status:**`, `**Target:**`, and `**Artifacts:**`.

Skip any step already marked `Done`. Resume — do not restart — any step marked `In Progress`: read its `**Status:**` note first and take what it says was already done as done. Re-doing a completed half of a step is how a resumed session quietly reverts a decision the previous one made.

For every step whose `**Artifacts:**` line is not `—`, read that step's artifacts directory before implementing anything. A previous run left those files there because they carry something the plan alone does not: a measurement, a query result, an extract, a correction. Treat what they establish as fact, and never re-run a probe whose output is already on disk. Also read `artifacts/shared/` and `artifacts/planning/` if they exist — a findings document in either may carry the premise the step was built on, or a later correction to it.

If any step references a file or class that does not exist yet, note it as a new file to be created. If any step is ambiguous or underspecified:

1. First consult `digest.md` — the **Acceptance Criteria**, **Description**, and **Discussion** sections often resolve ambiguity.
2. If still unclear, use best judgment based on the patterns already established in the relevant project. Record what was inferred — it will be included in the completion report.

Before writing any code, take the coding rules already loaded into this session that apply to the projects being modified — the conventions for their language, and the language-neutral ones. They apply unless a local convention overrides them.

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

1. Check the step for the specified path. Use it if given.
2. If no path is specified, infer placement from the project's directory structure (e.g. a new repository class goes where other repository classes live). Ask the user only when both signals are absent.
3. Write the file using the conventions established in Step 5.

#### Producing an artifact

A step may need to produce something that is **not** a change to the workspace — a read-only probe script, its captured output, a data extract, or a note recording what was found. These are legitimate, and for some kinds of work they are the *entire* deliverable rather than a by-product: the type file read in Step 2 says which.

Follow `ticket-common/ARTIFACTS.md` for placement, naming and the run-approval rule. In outline:

1. Create `artifacts/step-{N}.{M}/` for the step being implemented, or `artifacts/shared/` when the file serves more than one step.
2. Write the script there. Ask the user before running it — show what it does, what it reads, and that it writes nothing outside `artifacts/`. On approval, run it and capture its output beside it.
3. If the artifacts would not explain themselves to a later reader — what was run, against what, when, and what it showed — add a `README.md` to that directory saying so.
4. Set the step's `**Artifacts:**` line in the phase file to the paths just created, relative to the phase file, as `ticket-common/ARTIFACTS.md` → *The `**Artifacts:**` line* shows.

The approval in point 2 is required for every run of every script artifact, and a contradicting artifact stops the step — both per `ticket-common/ARTIFACTS.md` → *Running a script is always a separate permission*.

#### Keeping the step's status current

Set the step's `**Status:**` to `In Progress` before making its first edit, with a note saying the work has just begun, and keep that note current as the step's state materially changes. Run `plan-sync` after each status change, so the Progress table every other session sees stays true.

Where a step cannot be completed, do not leave it reading `In Progress`:

- **Blocked on an answer** — something outside the workspace must be decided or confirmed. Set `Blocked` with a note naming what is blocking and what would clear it, tell the user, and move to the next step in the phase if one is independent of it.
- **Blocked on a contradiction** — an artifact or the workspace contradicts what the step assumes. Follow `ticket-common/ARTIFACTS.md`: record it, tell the user, and ask whether to revise the plan — through `/ticket-plan`, since this skill never renumbers. Do not implement the step as written.
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

**If the build fails**, read the compiler output and see where each error is:

- **In a file this phase changed** → it is most likely caused by the changes just made. Fix it and re-run the build. If it still fails after one fix attempt, stop: report which project failed after which phase, with the compiler output, and ask the user to review it before continuing.
- **Only in files this phase did not touch** → another session working a parallel phase in the same project is the likely cause: its edits are on disk, half-finished. **Do not fix them.** Set the phase's last step `Blocked` — "build fails in `{file}`, outside this phase — likely another session's work in flight; re-build once it settles" — sync, report it with the compiler output, and do not continue to the next phase.

Either way, do not mark the phase complete or continue to the next phase until the build passes.

### Step 8 — Update the phase's status

First, check the phase against the type's completion rule from Step 2. Where the rule is not satisfied — a required test was not run, an invariant the type protects was broken, a deliverable the type demands was not produced — the phase is **not** done. Report what is missing, set the step's status accordingly, and stop rather than continuing to the next phase.

Then, once the build passes for all affected projects, edit the phase file:

1. Set `**Status:** Done` on every step that was actually completed. Leave a step that could not be completed as `Blocked` or `In Progress` with its note intact.
2. Set the `**Artifacts:**` line of every step that produced files to the paths under `artifacts/`, relative to the phase file; leave it `—` for steps that produced none.

Then run `plan-sync`. It derives the phase's status and every phase's readiness from the steps — a phase whose steps are not all `Done` is not `[x] Done`, however much of it ran — and its output names the phases this one just made Ready.

Then continue with the next selected phase at Step 4 — do not ask unless Step 4 must. After the last one, continue to Step 9.

### Step 9 — Report what the run produced

After all selected phases are complete, report what this run actually did.

Start with whatever the type file's *"What implement must produce"* section requires. That section is the completion report's first obligation, and for some kinds of work it is most of it — an answer and a recommendation, a before-and-after test result, a cause that turned out to differ from the hypothesis. Do not substitute the generic report below for it.

**Where the run changed source files**, identify which projects were modified, using two signals in order:

1. **The Workspace section's Projects table** — for each file created or edited, find the row whose directory holds it: the absolute path of the worktree or plain directory it lives in, joined with its `Path`. Use that row's project name.
2. **The file's worktree** — for a modified file no project row holds, walk up from it to the directory holding a `.git` entry: a directory in a main worktree, a file in a linked one. That directory is the worktree; report it, referred to as the glossary says, in place of a project.

**Where the run changed no source file**, say what it produced instead — the artifact paths, and what they establish. Do not report an empty project list, and do not imply something is missing; for a type whose deliverable is a written finding, that is a complete run. Check the type file before writing this sentence, not after.

Then report what this run decided and assumed, each naming the step it affects. This report is the only place either list is written down, so state it even when it feels obvious — `ticket-checkpoint` builds the session's journal entry from this conversation, and what was never said cannot be recorded.

Fill [`run-report.md`](./run-report.md): `{location}` is the worktree or plain directory, named as the glossary says, and `{filePath}` is relative to it. Omit Decisions or Inferences when it is empty. `Left in flight` reads `Nothing in flight.` when no step is left mid-way. `Now Ready` comes from the last sync: the phases not started whose dependencies and prerequisites are all met — each can be taken up in a session of its own.
