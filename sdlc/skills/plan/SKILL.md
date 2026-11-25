---
name: plan
description: Writes the plan.md of a ticket in the sdlc store, with a confirmed workspace and phased, file-level steps. On a ticket that has one, shows progress and updates step status. Use when asked to plan a ticket or update its plan.
argument-hint: "<ticket reference | spec file | text or idea> [directory ...] [ship]"
---

# Plan

Plan the ticket `$ARGUMENTS` names. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The formats are `${CLAUDE_PLUGIN_ROOT}/shared/plan.md` (template, statuses, project signals), `${CLAUDE_PLUGIN_ROOT}/shared/tdd.md` (test-first phases) and `${CLAUDE_PLUGIN_ROOT}/shared/types.md` (the five types). Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says, and `${CLAUDE_PLUGIN_ROOT}/shared/conventions.md` holds the rules about the workspace.

## Inputs

- The first word is a ticket reference, or the whole argument is a non-ticket input (a spec file, text or an idea). Trailing words that are existing directories are directories the user gave.
- No argument: the ticket this session has been working on, else ask which.
- `ship`: the [ship flag](../../shared/conventions.md#ship-runs), never part of the input or a directory. Each step below says what it decides in place of asking; every such decision also goes in the plan's Decisions section, as `${CLAUDE_PLUGIN_ROOT}/shared/plan.md` says.

## Steps

1. **Resolve.** Run `resolve <reference>`, adding `--context {namespace}[/{product}]` when the session has a context. If the ticket does not exist, or the argument is not a reference, do not fail: follow `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md` (one confirmation, none under `ship`) and carry on with the new ticket. A remote ticket that is not mirrored yet is fetched with `fetch`.
2. **Sync.** Run `sync <reference>` (with `--context`) and report it as `${CLAUDE_PLUGIN_ROOT}/shared/sync.md` says.
3. **Read the ticket directly.** A remote ticket's mirror is `raw/`; a local ticket's file is `raw/ticket.md`. Nothing is derived from it first. Prefer a dedicated field (reproduction steps, acceptance criteria) over the description. Open attachments, images and related tickets only when the plan needs what they hold. Read the type from `ticket.json`; if it has none, decide it, say so and record it there.
4. **A ticket that has a plan** goes to the re-run below instead of the next steps, unless the user asked for a new plan.
5. **Discover the workspace**: repositories, their worktrees, plain directories and projects. Start from the effective config's `scan_roots` (reported by `resolve`), the directories the user gave and the invocation directory, as `conventions.md` says. Never include the SDLC home or any ticket directory. Follow evidence, not proximity, to related repositories (submodules, relative project references). Where there is nowhere to look, ask; under `ship`, that is a question the run cannot settle: stop and report it. List only the worktrees the work happens in. Note a listed worktree whose branch is protected, as a prerequisite: `implement` will not edit there.
6. **Show the workspace and confirm it once** with the user, who can add, drop or correct. Nothing is planned before the yes. Under `ship`, show it and go on: the workspace is a decision, and a repository left in or out on weak evidence is named in it.
7. **Research by reading.** Read the files the plan will name, fully enough to name them correctly; never invent a file, class or command. What reading cannot settle, ask the user, or write as an assumption in the step that rests on it; under `ship`, write the assumption, and make it a decision when the plan's shape rests on it. When a fact the plan's shape depends on can be learned by running something, write a small probe script under `artifacts/planning/` with the header and run it only as `${CLAUDE_PLUGIN_ROOT}/shared/artifacts.md` says. Record what each probe found in `artifacts/planning/README.md`, and cite it on the **Artifacts:** line of every step that rests on it. Under `ship`, a probe that `effect` does not let run unasked is not run: the step rests on a written assumption instead, recorded as a decision.
8. **Offer test-first phases** as `tdd.md` says: where work has a seam a test can reach, propose the seams (and a test-setup phase where no test project exists), ask the user once, and wait. Nothing test-first is planned before the confirmation, and a bug's fix phase is a TDD phase whose first slice is the failing regression test. Under `ship`, decide the seams and any test-setup phase yourself on the same evidence, in place of the seam confirmation: each seam, each one passed over that the work could have used, and each test-setup phase is a decision.
9. **Write `plan.md`** from the template, with the phase shape the type calls for, and absolute paths in the Workspace section. Under `ship`, its Decisions section holds every decision of steps 3 to 8, and each TDD phase's `**Seams:**` line says they were decided by the ship run. Say where it is and show its Progress table.

## Re-run on a ticket with a plan

Do not regenerate it. Show the Progress table and every `In Progress` or `Blocked` step with its note, and ask what to update. Update only what the user says, or what the workspace evidences and the user confirms, honouring the status rules, and derive the Progress rows again. Revise only the steps a change affects. Under `ship`, ask nothing: show the table and the open steps, apply the statuses the workspace evidences, and change nothing else; a status set this way is a decision.

## Invariants

- The skill writes `plan.md` (and a missing `type` in `ticket.json`) and the probes and their captures under `artifacts/planning/`, nothing else beyond what `sync` writes. It writes no source code and changes nothing in the workspace.
- Git is used for reads only: no fetch, checkout, branch, worktree, commit or push, and nothing is ever written to a protected branch.
- A probe is never run unless `effect` says it may run unasked; any other waits for the user's approval of that run. Nothing that writes to an external system is run at all.
- TDD phases hold only confirmed seams, or under `ship` decided ones, and the plan records them. A phase that is not TDD over behaviour says why.
- Statuses are honest, as `plan.md` defines. A new plan holds `Pending` only.
- The ticket's content is read from the ticket, never copied into the plan.
- Do not read or write the journal.
