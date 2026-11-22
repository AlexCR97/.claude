---
name: intake
description: Bring a unit of work into the sdlc store as a ticket. For now, creates a new local ticket from a title.
disable-model-invocation: true
argument-hint: "<title>"
---

# Intake

Create a local ticket from the title in `$ARGUMENTS`. The ticket's file is the single source of truth: there is no mirror and no digest.

## Steps

1. Run `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" resolve --new --title "<title>"` (`python3` where that is the interpreter's name). It creates nothing; it prints JSON with the ticket's `ref` and, under `paths`, where to write it. A non-zero exit means the title cannot be filed (the stderr says why): stop and say so.
2. Decide the ticket's `type` from the title: `user-story`, `task`, `bug`, `spike` or `tech-debt`. Default to `task` when unclear.
3. Show the user the `ref`, the `type` and the directory, and ask for one yes before writing. Let them change the type or the title.
4. Write the two files, creating `raw/` as needed:
   - `ticket_json`: `{"source": "local", "id": "<id>", "title": "<title>", "type": "<type>", "url": null}`
   - `ticket_file`: `# <title>`, then `## Description` and `## Acceptance Criteria`, each holding only `TODO`. Establishing them is the author's work; never invent a criterion.
5. Report the `ref`, the `type` and `paths.ticket_dir`.

## Invariants

- Write only after the yes, and only at the paths `resolve` reported.
- Never overwrite a ticket: `resolve --new` exits non-zero when one exists.
