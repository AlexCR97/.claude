---
name: plan
description: Write a phased, file-level plan for a ticket into its ticket directory, after discovering and confirming the workspace. Run again on a ticket with a plan, it shows progress and updates step status.
disable-model-invocation: true
argument-hint: "<ticket reference | spec file | text or idea> [directory ...]"
---

# Plan

Plan the ticket `$ARGUMENTS` names. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The formats are `${CLAUDE_PLUGIN_ROOT}/shared/plan.md` (template, statuses, project signals) and `${CLAUDE_PLUGIN_ROOT}/shared/types.md` (the five types). Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says, and `${CLAUDE_PLUGIN_ROOT}/shared/conventions.md` holds the rules about the workspace.

## Inputs

- The first word is a ticket reference, or the whole argument is a non-ticket input (a spec file, text or an idea). Trailing words that are existing directories are directories the user gave.
- No argument: the ticket this session has been working on, else ask which.

## Steps

1. **Resolve.** Run `resolve <reference>`, adding `--context {namespace}[/{product}]` when the session has a context. If the ticket does not exist, or the argument is not a reference, do not fail: follow `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md` (one confirmation) and carry on with the new ticket. A remote ticket that is not mirrored yet is fetched with `fetch`; if that verb is missing, stop and say the mirror is absent.
2. **Read the ticket directly.** A remote ticket's mirror is `raw/`; a local ticket's file is `raw/ticket.md`. There is no digest. Prefer a dedicated field (reproduction steps, acceptance criteria) over the description. Open attachments, images and related tickets only when the plan needs what they hold. Read the type from `ticket.json`; if it has none, decide it, say so and record it there.
3. **A ticket that has a plan** goes to the re-run below instead of the next steps, unless the user asked for a new plan.
4. **Discover the workspace**: repositories, their worktrees, plain directories and projects. Start from the effective config's `scan_roots` (reported by `resolve`), the directories the user gave and the invocation directory, as `conventions.md` says. Never include the SDLC home or any ticket directory. Follow evidence, not proximity, to related repositories (submodules, relative project references). Where there is nowhere to look, ask. List only the worktrees the work happens in. Note a listed worktree whose branch is protected, as a prerequisite: `implement` will not edit there.
5. **Show the workspace and confirm it once** with the user, who can add, drop or correct. Nothing is planned before the yes.
6. **Research by reading.** Read the files the plan will name, fully enough to name them correctly; never invent a file, class or command. What reading cannot settle, ask the user, or write as an assumption in the step that rests on it.
7. **Write `plan.md`** from the template, with the phase shape the type calls for, and absolute paths in the Workspace section. Say where it is and show its Progress table.

## Re-run on a ticket with a plan

Do not regenerate it. Show the Progress table and every `In Progress` or `Blocked` step with its note, and ask what to update. Update only what the user says, or what the workspace evidences and the user confirms, honouring the status rules, and derive the Progress rows and Total again. Revise only the steps a change affects.

## Invariants

- The skill writes `plan.md` (and a missing `type` in `ticket.json`), nothing else. It writes no source code and changes nothing in the workspace.
- Git is used for reads only: no fetch, checkout, branch, worktree, commit or push, and nothing is ever written to a protected branch.
- Test-first phases and probe scripts are not planned yet: use the Development and Testing activities and ask where a fact needs running to learn.
- Statuses are honest, as `plan.md` defines. A new plan holds `Pending` only.
- The ticket's content is read from the ticket, never copied into the plan.
- Do not read or write the journal.
