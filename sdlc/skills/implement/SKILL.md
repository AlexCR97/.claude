---
name: implement
description: Implements one, several or all phases of a ticket's plan.md by making the code changes each step names, then building and testing the affected projects. Keeps step status honest, never writes to a protected branch, and never commits or pushes unasked.
disable-model-invocation: true
argument-hint: "<ticket reference | spec file | text or idea> [phases | all]"
---

# Implement

Carry out the phases of the plan of the ticket `$ARGUMENTS` names. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). Formats: `${CLAUDE_PLUGIN_ROOT}/shared/plan.md` (statuses), `${CLAUDE_PLUGIN_ROOT}/shared/types.md` (completion rules) and `${CLAUDE_PLUGIN_ROOT}/shared/guard.md` (protected branches, branch and worktree naming). Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- The ticket: a reference, or a non-ticket input, which you adopt first as `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md` says. Resolve with `resolve <reference>`, adding `--context {namespace}[/{product}]` when the session has one. No argument: the ticket this session has been working on, else ask.
- The phases: a comma-separated list of phase numbers or `all` (every phase not `Done`, in order). Absent, show the Progress table and ask. A `Done` phase is skipped with a warning; an `In Progress` step is resumed from its note, never restarted; a `Blocked` phase is not run silently: report the block and ask.
- `plan.md` must exist; if it does not, say `/sdlc:plan` comes first and stop.

## Before the first edit

1. **Open blockers warn, they do not refuse.** Read the ticket's blockers with their state from its mirror (for GitHub `raw/raw.json`, `blocked_by`; for other sources read whatever relations the mirror holds, such as predecessors). If any is open, name it and ask whether to start anyway. A local ticket has none.
2. **Protected branches.** For each worktree in the plan's Workspace section that the chosen phases change, ask `guard check --op edit --repo <worktree directory>`. A `default_branch_source` of `unknown` means the default branch could not be determined: say so and ask which it is before going on. Refuse to start while any is refused: name each worktree and its branch, then offer one ticket branch and one ticket worktree per repository the chosen phases change, named as `guard.md` says. First `git fetch` there and report each workspace worktree's staleness (commits behind `origin/{default branch}`), then cut from the up-to-date default branch. On a yes, create them, rewrite the plan's Workspace section (and any path to the old worktree in `plan.md` and `artifacts/`) to match with a one-line note why, and work in the new worktrees. On a no, stop. A workspace already on ticket branches proceeds with no offer, and so does a run whose phases write only under `artifacts/`, such as a spike's.
3. Read `plan.md` and the type from `ticket.json`. Read the ticket's `artifacts/` for what earlier runs established; treat it as fact and do not re-run a probe whose output is on disk.

## Doing the work

- Work only in the worktrees and plain directories the Workspace section lists, only in the chosen phases, and only on what each step names. Resolve a `**Target:**` against the absolute path recorded for its worktree.
- Read a file fully before editing it, make targeted edits, follow the project's own conventions, and add nothing the step does not require.
- A TDD phase's steps are slices, built one at a time as the Implementing section of `${CLAUDE_PLUGIN_ROOT}/shared/tdd.md` says. Red comes first: run the step's test alone and see it fail for the missing behaviour before touching any production file, and say the test's name, its red failure message and its green result as the slice finishes. Update the step's status note slice by slice. A confirmed seam that is missing or does not reach the behaviour sets the step `Blocked` and asks where the test should sit.
- Mark a step `In Progress` with its note **before** its first edit, and keep the note current. Where it cannot finish, set `Blocked` with what blocks it and what would clear it; never leave a stale `In Progress`. Mark it `Done` only when its work is. Never write a bare `In Progress` or `Blocked`, and derive a phase's Progress row from its steps: never `[x] Done` while a step is not `Done`.
- After a phase, build each affected project and run the tests that cover it, detecting tools from the project's files. A phase that changed no source file has nothing to build. If a build or test still fails after one fix attempt, stop and report with the output; do not mark the phase done or go on to the next. A failing test is fixed in production code, never by changing its assertion.
- Non-code files go under `artifacts/step-{N}.{M}/` or `artifacts/shared/`, never overwriting or deleting an existing one, and each producing step's `**Artifacts:**` line is kept accurate. Never write into `artifacts/planning/`.
- Say every decision and inference in chat as it is made, with the step it affects: `checkpoint` builds its entry from this conversation.
- After each phase offer `/sdlc:document` for the projects that phase changed, as `<reference> <phase>`; never run it unasked.

## Completion rule of the type

Apply `types.md` both ways, and report what it requires for the type first. Two inversions are gates: a `spike` that changes no source file succeeded, and a `tech-debt` run in which an existing test's assertion had to change **failed**: stop, report each such assertion and do not fix it to pass. A purely mechanical edit (rename, namespace, constructor signature) is allowed and listed one by one.

## Report

What the run produced (per project, or the artifacts for a run that changed no source), the build and test results, what was left in flight, and every decision and inference.

## Invariants

- Never write to a protected branch, and never edit in a worktree that has one checked out: the guard decides, and a refusal is final.
- Never commit, push or open a pull request unless the developer asks.
- Run only read-only, build and test commands. Never install a package or change the environment.
- Never read or write the journal.
- Statuses in `plan.md` are honest, as `plan.md` defines.
