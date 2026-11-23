---
name: document
description: Brings the README of each project a change touched (an sdlc ticket's phase, or a set of paths) back in line with the code, touching only the sections the change affects. Use when asked to document the changes of an sdlc ticket or one of its phases.
argument-hint: "[<ticket reference> <phase> | <paths or projects> | all] [ship]"
---

# Document

Bring the README of each project the change touched back in line with the code. Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name).

## Inputs

- `<ticket reference> <phase>` (also what `implement` hands over): resolve the ticket with `resolve <reference>`, adding `--context {namespace}[/{product}]` when the session has one. The scope is the files that phase changed: its steps' targets in `plan.md`, plus git reads in each worktree of the plan's Workspace section (the diff of the ticket branch against its base, and uncommitted changes).
- Paths or projects: exactly those.
- `all`, or a project that has no README yet: a whole-project pass.
- No argument: the projects with uncommitted or branch changes in the invocation directory; ask if that is unclear.
- `ship`: the [ship flag](../../shared/conventions.md#ship-runs), never part of the scope. `implement` passes it under a ship run, always with a ticket and a phase. Under it, what this skill would have asked about stays out of the README and is named in the report, and a section it adds is a decision.

## Outputs

Edits to the README of each project in scope: the README of the project or repository that changed, inside the worktree the change lives in, so the update lands in the same diff as the code. A change under a project with no README of its own goes to the repository's.

## How

- Read the changed code, then the README. Decide which sections the change makes wrong or incomplete (a new command, flag, setting, module, requirement or behaviour) and edit only those. Every other line stays byte-identical, including wording, wrapping and heading order you would have written differently.
- A change that nothing in the README covers gets the smallest addition under the section it belongs to; if no section fits, add one and say so.
- A whole-project pass writes or rewrites the README from the code. The checklist is what a README covers: title, overview, terminology and domain logic where the code has any, architecture and how the parts connect, setup (prerequisites, tools, environment and configuration variables), how to run, debug and test, key or complex code, troubleshooting, references. Include what the project has and skip the rest; a heading with nothing under it does not belong.
- Read the code for every statement. Where it cannot tell (intent, an external system, a command you could not confirm), ask, or leave it out. Never paraphrase the ticket or plan as fact about the code.

## Report

Per README: what changed, section by section. Then anything found undocumented or stale that you left alone because it is outside the scope.

## Invariants

- Write only after the offer from `implement` was accepted, the developer invoked this skill, or a ship run's `implement` ran it with `ship`; never as a side effect of another skill.
- Never commit, push or open a pull request.
- Change no source code, plan or ticket file; the READMEs are the only files written.
- Make no claim the code does not support.
