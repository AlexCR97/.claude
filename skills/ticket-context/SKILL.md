---
name: ticket-context
description: Sets, shows or clears the session context — the namespace, and optionally the product, this conversation works in. Every other ticket-* skill then prefers it when resolving a reference, filing a new ticket or listing tickets.
argument-hint: "[namespace[/product] | clear]"
allowed-tools: Bash(python *ticket.py:*)
---

Sets, shows or clears the session context — the namespace, and optionally the product, a conversation works in. Without one, every ticket skill looks across every namespace: a bare id that exists in two namespaces stops to ask, and a "which ticket?" listing shows everything on the machine. With one, every later skill prefers it when resolving a reference, filing a new ticket or listing tickets, per `ticket-common/RESOLUTION.md` → *The session context*.

End state: the context set, shown or cleared in this conversation, and nothing written on disk.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names     |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | not read by this skill |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`[namespace[/product] | clear]`** — a namespace, or a namespace and product, sets the context; `clear` clears it; absent, the current context is shown. The terms mean what `ticket-common/GLOSSARY.md` says.

---

## Ground rules

1. **Write nothing.** The context lives in this conversation; never save it to a file, a config or an environment variable.
2. **Set only a context that exists.** Report a missing one and point at `/ticket-setup --in`.
3. **Never infer a context** from the branch name or the invocation directory. This skill sets it, or `/ticket-resume` adopts it from a ticket the user chose.
4. **Never let a context change a ticket already filed.** A ticket's scan roots and bindings always come from its own product.

---

## Execution Steps

### Step 1 — Decide what was asked

- **`namespace[/product]`** → set it. Continue to Step 2.
- **`clear`** → clear it. Skip to Step 4.
- **Nothing** → show it. Skip to Step 3.

### Step 2 — Set it

Check that it exists, and read what it holds:

```bash
python "{skills}/ticket-common/ticket.py" namespaces --in "namespace[/product]"
```

- **Exit 0:** print the line `Ticket context:` followed by the context in backticks. Then print one line summarizing the output: the default source, what each source is bound to, where the scan roots come from, and how many tickets it holds. For a namespace-only context, add that a new ticket goes to its default product — `default_product` in the output — unless a more specific rule picks another.
- **Exit 5:** it does not exist. Set nothing. Run `python "{skills}/ticket-common/ticket.py" namespaces`, list the namespaces and products that do exist, and point at `/ticket-setup --in namespace[/product]` to create it.
- **Any other non-zero exit:** report the message and its hint verbatim, and set nothing.

The `Ticket context:` line is what later skills look for. It is the whole of the state: this skill writes nothing anywhere.

Stop.

### Step 3 — Show it

Find the most recent `Ticket context:` line in this conversation that a later `/ticket-context clear` has not cancelled.

- **There is one** → re-run Step 2's `namespaces --in` for it and print the same two lines, so what is shown is what is on disk now.
- **There is none** → report that no ticket context is set, that every ticket skill looks across all namespaces, and that `/ticket-context namespace[/product]` sets one.

Stop.

### Step 4 — Clear it

> Ticket context cleared. Every ticket skill looks across all namespaces again.
