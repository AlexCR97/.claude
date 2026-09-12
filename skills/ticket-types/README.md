# Ticket types

This directory is **not a skill** — it holds no `SKILL.md`. It holds one file per ticket type, discovered by glob. Adding a type is adding a file; no `SKILL.md` changes.

Type is the second modular axis, orthogonal to the first. **The source decides how to talk to whatever holds the ticket. The type decides what shape the work is and what proves it done.** Nothing about a type depends on where the ticket came from, and nothing about a source depends on what kind of work it describes.

Five types exist today. The set is open.

| File | Shape of the work |
| --- | --- |
| `user-story.md` | New observable behaviour for a user |
| `task.md` | A bounded, self-evident change |
| `bug.md` | Something is wrong and must stop being wrong |
| `spike.md` | A time-boxed question whose deliverable is a written finding |
| `tech-debt.md` | Restructuring that must leave behaviour unchanged |

---

## The six questions

Every type file answers the same six questions, in this order, under these headings. A driver reads only the sections it needs, so the headings are part of the contract.

1. **What this type is** — one paragraph. What distinguishes it from its nearest neighbour.
2. **What refine must establish** — the questions that are non-negotiable for this type, folded into the driver's own rounds.
3. **What digest must surface** — which sections matter, and which source field to prefer when several could fill one.
4. **What shape the plan takes** — required phases, forbidden phases, the kind of thing a step delivers, the activity mix, and any estimate adjustment.
5. **What done means** — the completion test, stated so it can be checked rather than asserted.
6. **What implement must produce** — what the run has to show for itself before a phase may be reported complete.

A type file that cannot answer one of these says so explicitly. Silence reads as "the default applies", which is only true when it was written on purpose.

---

## The anti-leak rule

> **A type file must never mention a source.** No field key, no URL, no API, no credential, no markup dialect, no store layout.

If a rule cannot be written without naming where the ticket came from, it is not a property of the type — it belongs in that source's directory. The one place the two axes meet is each source's own `types.md`, which maps that source's vocabulary onto one of the names here. That mapping lives on the source side, and it is a mapping only: a source file never encodes what a type *does*.

The converse holds too. A type file describes the shape of work and the test for done; it never restates a driver's step ordering, its output template, or anything in `ticket-common/`.

---

## Resolution and override

A ticket's type is resolved once, by the source's `types.md`, and recorded in `ticket.json`. Every later skill reads it from there rather than re-deriving it, so they cannot disagree.

Any driver accepts `--type {type}` to override. The override is recorded in `ticket.json` alongside the untouched `native_type`, so a following skill inherits it with no flag.

When a native type maps to nothing here, fall back to `task` **and say so in one line**. Never silently.

---

## Adding a type

Write one file named for the canonical type, answer the six questions, and add the mapping to each source's `types.md` that can express it. A type no source can produce is still reachable through `--type`, which is the normal way a new type gets used before any source learns to label it.
