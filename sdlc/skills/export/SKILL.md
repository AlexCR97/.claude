---
name: export
description: Writes an archive (a zip) of the SDLC home, or of one namespace, product or ticket in it, to carry that work to another machine. Use when asked to export, archive or move sdlc tickets, plans or journals off this machine.
argument-hint: "[<namespace> | <namespace>/<product> | <ticket reference>] [where to write it]"
---

# Export

Write an archive of what `$ARGUMENTS` names. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The archive's format is `${CLAUDE_PLUGIN_ROOT}/shared/archive.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The scope**: nothing for the whole SDLC home, a namespace, `{namespace}/{product}`, or a ticket reference. Pass it through as written; the verb decides which it is.
- **Where to write it**, if given: a zip path or a directory, as `--out`. Otherwise the invocation directory.
- Add `--context {namespace}[/{product}]` when the session has a context, so a short ticket reference means the nearest ticket.

## Run

`archive export [<scope>] [--out <path>] [--context {namespace}[/{product}]]`. It prints JSON: `archive` (the zip's path), `scope` (`kind` and `ref`), `tickets` (how many it holds), `created_at` and `source_home`.

- Exit 3: the argument is ambiguous. Show the candidates the error lists and ask which; run again with the one chosen.
- Exit 1: report the error and its hint. A scope that is not in the home, an existing zip and a path inside the SDLC home are refused; nothing was written.

## Report

One short message: the zip's path, the scope (`home`, or its kind and reference) and how many tickets it holds. Then one line: carry the zip by hand, and merge it on the other machine with `/sdlc:import`.

## Invariants

- Reads the SDLC home and writes one new zip outside it. Never changes, moves or deletes anything in the home, and never overwrites a file.
- Upload, send or commit the zip only when the user asks; an archive holds every journal entry and artifact of its scope.
