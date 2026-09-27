---
name: ticket-move
description: Re-files a ticket under another namespace and product. Renames its directory in place, rewrites every parent reference that would stop resolving, and reports the links the move breaks. Shows a dry run and asks before moving anything.
argument-hint: "<[namespace/product/][source:]id> <namespace/product>"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory                    | Contains                                                                                                          | Read                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names     |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | not read by this skill |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill |

Never let a source-specific or type-specific fact creep back into this file. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`.**

No `allowed-tools` here: this skill renames a directory whose path is not known in advance.

---

## Purpose

A ticket is filed under the product the filing rules chose when it arrived — often a fallback product, when nothing said where it belonged. This skill files it where it does belong. Namespace, product, filing and every other term here mean exactly what `ticket-common/GLOSSARY.md` says.

**It renames; it never copies.** `journal.md` cannot be regenerated, and a rename carries every byte of it or none, with no second copy to diverge.

Re-filing changes where a ticket is kept, never where it lives upstream: its own coordinates stay in its `ticket.json`, so it still fetches from exactly where it did. What a rename cannot carry is anything that pointed at the old place:

- **`parent` references** are data the suite resolves, so the move rewrites them — on the moved ticket, and on every child that names it — to whatever still resolves from where each one is filed.
- **Links in prose** are reported, not rewritten. A journal entry is never edited, and the rest is someone's writing.

---

## Input

```
/ticket-move <[{namespace}/{product}/][{source}:]{id}> <{namespace}/{product}>
```

- `{ref}` — the ticket. When omitted, ask; never guess.
- `{namespace}/{product}` — where it goes. When omitted, ask, listing the products `ticket.py namespaces` reports.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the ticket

When this session has a session context, pass `--context {context}` and start your first output line with `Ticket context: {context}` — see `ticket-common/RESOLUTION.md` → _The session context_.

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require ticket_dir [--context {context}]
```

Everything below uses the `qualified_ref` and `product` it returns. On a non-zero exit, report the message and its hint verbatim and stop.

### 2. Check the destination

```bash
python "{skills}/ticket-common/ticket.py" namespaces --in "{namespace}/{product}"
```

- **Exit 5** — it does not exist yet. The move would create it, and a mistyped name would become a product nobody meant. Ask: `{namespace}/{product} does not exist — create it by moving the ticket there? [y/N]`. On no, stop.
- **It is the ticket's own product** — say so and stop; there is nothing to do.

### 3. Dry-run the move

```bash
python "{skills}/ticket-common/ticket.py" move "{qualified_ref}" --to "{namespace}/{product}" --dry-run
```

It moves nothing. It refuses — exit 1, reported verbatim — when the destination is bound to other coordinates than the ticket's, since a ticket is never filed against its own identity; when a ticket of that id is already there, since a move never merges; and when a `parent` it would have to rewrite cannot be written, which it finds out now by trying each one without writing.

Show, from its output:

- `from` → `to`
- **References it will rewrite** — each ticket, the old `parent` text, the new one
- **An unresolved parent**, when `unresolved_parent` is set: the ticket names a parent that resolves nowhere, and the move leaves it as written
- **Links the move breaks**, grouped by file — the replacement that would repair each, and that nothing rewrites them
- **Links already broken** in the ticket's own files, in one line with a count; list them only if asked
- **Files quoting the ticket's old absolute path**

### 4. Confirm

> Move `{from}` to `{to}`? {N} references rewritten, {N} links left broken. [y/N]

Wait for an explicit yes.

### 5. Move it

```bash
python "{skills}/ticket-common/ticket.py" move "{qualified_ref}" --to "{namespace}/{product}"
```

On a non-zero exit, report the message verbatim and stop. Nothing was changed: a rename that fails — usually because a terminal or an editor holds the directory open — leaves the ticket where it was, and the hint says so.

### 6. Report

> Moved `{from}` to `{to}` — `{to_dir}`.

Then, in a line each, only where they apply:

- The references rewritten.
- **Every reference that could not be rewritten**, when `result` is `moved_with_errors`: each entry in `references_failed`, with the `parent` it should now hold and why it failed, so it can be set by hand. The ticket has moved either way.
- The links left broken, by file, with the replacement for each, so they can be fixed by hand. For a link inside `journal.md`, say that journal entries are never edited, so it stays as written.
- When a session context is set and the ticket is now outside it, say so.

---

## Constraints

- Never move without showing the dry run and getting an explicit yes
- Never copy a ticket directory, and never merge into an existing one
- Never edit `journal.md`, and never rewrite a link in any file — report it
- Never re-file a ticket under a product bound to other coordinates than its own
- Never infer the ticket from the branch name — use the argument, or ask
