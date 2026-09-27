---
name: ticket-context
description: Sets, shows or clears the session context — the namespace, and optionally the product, this conversation works in. Once set, every other ticket-* skill in the session prefers it when resolving a reference, files new tickets under it, and narrows its ticket listings to it. Optional, and lasts only for this conversation. Makes NO changes on disk.
argument-hint: "[namespace[/product] | clear]"
allowed-tools: Bash(python:*)
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory                    | Contains                                                                                                          | Read                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names     |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | not read by this skill |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill |

Never let a source-specific or type-specific fact creep back into this file. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`.**

**`allowed-tools` is set on this skill deliberately.** It changes nothing on disk — the context lives in the conversation — so an allowlist costs nothing and makes that mechanically true.

---

## Purpose

A session usually works in one body of work: EdWire's EW.Educate, say, or a personal notes app. Without a session context, every skill looks across every namespace — a bare `ado:18585` that exists in two organizations stops to ask, a new local ticket goes to the default product, and a "which ticket?" listing shows everything on the machine.

With one, the session says where it is once, and every later skill uses it consistently:

- **Resolving** — a reference means the nearest ticket of that name: in the context's product, then its namespace, then everywhere. A ticket found only outside the context still resolves, with a one-line note.
- **Filing** — a new ticket goes under the context's product, as long as that product can hold it. A remote ticket still needs a binding for its source, and a pasted address still goes where its coordinates say.
- **Listing** — `/ticket-resume` and `/ticket-checkpoint` show the tickets in the context first, with a count of the rest.

It never changes anything about a ticket already filed: a ticket's scan roots and bindings always come from its own product.

What session context, namespace and product mean is in `ticket-common/GLOSSARY.md`; how every driver passes the context on is in `ticket-common/RESOLUTION.md` → _The session context_.

---

## Input

```
/ticket-context {namespace}[/{product}]   set it
/ticket-context                           show it
/ticket-context clear                     clear it
```

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Decide what was asked

- A `{namespace}` or `{namespace}/{product}` → set it. Continue to step 2.
- `clear` → clear it. Skip to [step 4](#4-clear-it).
- Nothing → show it. Skip to [step 3](#3-show-it).

### 2. Set it

Check that it exists, and read what it holds:

```bash
python "{skills}/ticket-common/ticket.py" namespaces --in "{namespace}[/{product}]"
```

**Exit 5 means it does not exist.** Do not set it. Run `ticket.py namespaces`, list what does exist, and offer the way to create it:

> `{scope}` does not exist. Existing: `edwire/ew-educate`, `personal/notes-app`. Run `/ticket-setup --in {scope}` to create it.

On success, print the context on its own line, then one line summarizing what it holds, from the output:

> Ticket context: `edwire/ew-educate`
> Default source `ado` · ado bound to organization 'edwire', project 'EW.Educate' · scan roots from `edwire/config.json` · 24 tickets

For a namespace-only context, add that a new ticket goes to its default product — `default_product` in the output — unless a more specific rule picks another.

The `Ticket context:` line is what later skills look for. It is the whole of the state: this skill writes nothing anywhere.

### 3. Show it

Find the most recent `Ticket context:` line in this conversation that a later `/ticket-context clear` has not cancelled.

- **There is one** → re-run step 2's `namespaces --in` for it and print the same two lines, so what is shown is what is on disk now.
- **There is none** →

  > No ticket context is set. Every ticket skill looks across all namespaces. Set one with `/ticket-context {namespace}[/{product}]`.

### 4. Clear it

> Ticket context cleared. Every ticket skill looks across all namespaces again.

---

## How later skills use it

This is the contract every other `ticket-*` skill follows, restated here so the user can see what they just switched on. `RESOLUTION.md` is the authority.

- The **most recent** `/ticket-context` in the conversation wins; `clear` ends it.
- Every `ticket.py` call that takes one gets `--context {context}`, and every skill's first output line is `Ticket context: {context}`.
- An explicit `--in` or qualified reference in an invocation overrides the context for that one call, and the skill says so.
- `/ticket-resume` adopts the resumed ticket's product as the context when none is set, and says so. It never replaces one that is set.
- `/ticket-checkpoint` asks before writing a journal entry on a ticket filed outside the context.

---

## Constraints

- **Write nothing.** The context lives in this conversation; never save it to a file, a config, or an environment variable
- Never set a context that does not exist — report it and point at `/ticket-setup --in`
- Never infer a context from the branch name or the invocation directory — it is set by this skill, or adopted by `/ticket-resume` from a ticket the user chose
- Never let a context change anything about a ticket already filed
