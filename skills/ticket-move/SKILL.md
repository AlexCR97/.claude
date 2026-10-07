---
name: ticket-move
description: Re-files a ticket under another namespace and product. Renames its directory in place, rewrites every parent reference that would stop resolving, and reports the links the move breaks. Shows a dry run and asks before moving anything.
argument-hint: "<ref> <namespace/product>"
allowed-tools: Bash(python *ticket.py:*)
---

Re-files a ticket under another namespace and product: renames its directory in place, rewrites every `parent` reference that would stop resolving, and reports the links the move breaks. A ticket is filed where the filing rules put it when it arrived — often a fallback product — and this skill files it where it belongs. Re-filing changes where a ticket is kept, never where it lives upstream. `ticket-common/RESOLUTION.md` → *Moving* says what a move rewrites and what it only reports; the terms mean what `ticket-common/GLOSSARY.md` says.

End state: the ticket directory under the destination product, every `parent` that named it rewritten or reported as failed, and every link the move broke reported with its replacement.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names     |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | not read by this skill |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`<ref>`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Ask when it is absent; never guess.
- **`<namespace/product>`** — the product to re-file it under. Ask when it is absent, listing the products `python "{skills}/ticket-common/ticket.py" namespaces` reports.

---

## Ground rules

1. **Never move without the dry run and an explicit yes.** Show the dry run first; anything short of yes moves nothing.
2. **Rename; never copy or merge.** `journal.md` cannot be regenerated, and a rename carries every byte of it or none — never into an existing ticket directory.
3. **Never rewrite a link, and never edit `journal.md`.** Report every broken link instead.
4. **Never re-file a ticket under a product bound to other coordinates than its own.**
5. **Never infer the ticket from the branch name.** Use the argument, or ask.

---

## Execution Steps

### Step 1 — Resolve the ticket

When this session has a session context, pass `--context {context}` and open the first output line with `Ticket context: {context}` — see `ticket-common/RESOLUTION.md` → *The session context*.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require ticket_dir [--context {context}]
```

Everything below uses the `qualified_ref` and `product` it returns. On a non-zero exit, report the message and its hint verbatim and stop.

### Step 2 — Check the destination

```bash
python "{skills}/ticket-common/ticket.py" namespaces --in "<namespace/product>"
```

- **Exit 0, and it is the ticket's own product** → say there is nothing to do. Stop.
- **Exit 0** → continue to Step 3.
- **Exit 5** → it does not exist yet. The move would create it, and a mistyped name would become a product nobody meant. Ask whether to create it by moving the ticket there, defaulting to no. On yes, continue to Step 3; on no, stop.
- **Any other non-zero exit** → report the message and its hint verbatim. Stop.

### Step 3 — Dry-run the move

```bash
python "{skills}/ticket-common/ticket.py" move "{qualified_ref}" --to "<namespace/product>" --dry-run
```

It moves nothing.

- **Exit 1** → it refuses: the destination is bound to other coordinates than the ticket's, a ticket of that id is already there, or a `parent` rewrite it owes cannot be written. Report the message verbatim. Stop.
- **Any other non-zero exit** → report the message and its hint verbatim. Stop.
- **Exit 0** → show, from its output:
  - `from` → `to`
  - **References it will rewrite** — each ticket, the old `parent` text, the new one
  - **An unresolved parent**, when `unresolved_parent` is set: the ticket names a parent that resolves nowhere, and the move leaves it as written
  - **Links the move breaks**, grouped by file — the replacement that would repair each, and that nothing rewrites them
  - **Links already broken** in the ticket's own files, in one line with a count; list them only if asked
  - **Files quoting the ticket's old absolute path**

### Step 4 — Confirm

Ask whether to move `from` to `to`, with the number of references it rewrites and links it leaves broken, defaulting to no.

- **An explicit yes** → continue to Step 5.
- **Anything else** → move nothing. Stop.

### Step 5 — Move it

```bash
python "{skills}/ticket-common/ticket.py" move "{qualified_ref}" --to "<namespace/product>"
```

On a non-zero exit, report the message verbatim and stop. Nothing was changed: a rename that fails — usually because a terminal or an editor holds the directory open — leaves the ticket where it was, and the hint says so.

### Step 6 — Report

Report that the ticket moved from `from` to `to`, and its new directory `to_dir`. Then, in a line each, only where they apply:

- The references rewritten.
- **Every reference that could not be rewritten**, when `result` is `moved_with_errors`: each entry in `references_failed`, with the `parent` it should now hold and why it failed, so it can be set by hand. The ticket has moved either way.
- The links left broken, by file, with the replacement for each, so they can be fixed by hand. For a link inside `journal.md`, say that journal entries are never edited, so it stays as written.
- When a session context is set and the ticket is now outside it, say so.
- How to undo it: move it back with `/ticket-move`, from `to` to the product in `from`.
