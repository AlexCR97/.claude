---
name: intake
description: Bring a unit of work into the sdlc store as a local ticket, from a spec file, pasted text or idea, or the current branch.
disable-model-invocation: true
argument-hint: "[<spec file path> | <text or idea>]"
---

# Intake

Turn what `$ARGUMENTS` holds into a new local ticket by following `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md`. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name).

## Inputs

- A path to a spec or markdown file: its content is copied into the ticket and the path is recorded as `origin`.
- Pasted text or an idea: it becomes the ticket's description.
- No argument: offer a new ticket for the current branch's work, titled from the branch, and ask what the work is. The branch never identifies an existing ticket.

## Outputs

A new local ticket under the sdlc home: `ticket.json` and `raw/ticket.md` at the paths `resolve --new` reported. Report its `ref`, its `type` and its directory.

## Invariants

- When the session has a context (`/sdlc:setup`), pass `--context {namespace}[/{product}]` to `resolve`, and tell the user where the ticket will be filed.
- Ask once, and write nothing before the yes.
- Copy the content; the ticket's file is its single source of truth, with no mirror.
- The model decides the type, says so, and the user can override it.
- Never overwrite an existing ticket.
