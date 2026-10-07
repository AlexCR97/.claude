---
name: ticket-create
description: Creates a ticket in a store that supports it, seeded from its type so the body starts with the right questions, then chains into ticket-refine. For local tickets that have no upstream system to fetch from.
argument-hint: "<title> [--source source] [--type type] [--in namespace[/product]] [--parent ref]"
allowed-tools: Read Edit Skill Bash(python *ticket.py:*)
---

Creates a ticket in a store that supports it — work with no upstream system, such as a refactor decided this morning or a bug found in-house — seeds its body from its type so it starts with the right questions, and hands straight to `/ticket-refine`. It does not interview: establishing what the work is belongs to refinement, so acceptance criteria stay a `TODO` stub.

End state: a new ticket directory under the product the user confirmed, its body seeded from its type with acceptance criteria left as a `TODO`, and the run handed to `ticket-refine` — or stopped at the user's word, with the way back named.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file                                             |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`<title>`** — the ticket's title, quoted when it has spaces. Ask for one when it is absent.
- **`[--source source]`** — the store to create it in. Step 2 resolves `{source}` from it.
- **`[--type type]`** — the kind of work. Step 3 resolves `{type}` from it.
- **`[--in namespace[/product]]`** — the namespace or product to file it under, overriding the filing rules. Namespace, product and filing mean what `ticket-common/GLOSSARY.md` says.
- **`[--parent ref]`** — for a task, the reference of the parent user story it belongs to. The source's `new.md` says whether it accepts this and how it is stored. When it is absent for a task, the seeded stub from Step 5 and `/ticket-refine` establish it.

---

## Ground rules

1. **Report a missing capability as a gap.** Never create a ticket in a source that declares no `new`, and never substitute another source's file for a missing one.
2. **Never interview.** Establishing what the work is belongs to `/ticket-refine`.
3. **Never invent content.** Leave acceptance criteria as a `TODO` stub, and make every seeded section a prompt, not an answer.
4. **Never pick a type silently.** Ask; the type shapes every skill downstream.
5. **Show the filing before creating.** Never create a ticket without showing its slug and the product it is filed under, and letting the user change either.
6. **Never write into an existing ticket directory.** A collision is a different slug, never a merge.
7. **Write only what the store's `new.md` describes** into the ticket directory.

---

## Execution Steps

### Step 1 — Enumerate what is available

With a session context, pass `--context {context}` on every `ticket.py` call below that takes one and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" sources
```

This gives the installed sources with their capabilities, and `known_types` — the list of ticket types. **Never assume a fixed set of either**; both are discovered by glob, and both grow by adding a file.

### Step 2 — Resolve the source

- **Supplied, and its `capabilities.new` is true** → use it.
- **Supplied, with no `new`** → refuse: report that `{source}` cannot create tickets because its tickets are created in the system that backs it, and point at creating it there and running `/ticket-fetch` instead. Stop.
- **None supplied, and one source has `new`** → use it.
- **None supplied, and several have `new`** → list them and ask.
- **None supplied, and none has `new`** → report that no installed source can create tickets. Stop.

A refusal is a **reported gap, not a fallback**. The absence of that source's `new.md` documents that creating an upstream ticket is out of scope — do not improvise an API call, and do not silently create it locally instead.

### Step 3 — Resolve the type

Take the type the user supplied. If they supplied none, offer the list from Step 1 and ask — one line each, from the first paragraph of each type file. Do not default silently: type decides the shape of everything downstream, and it is much cheaper to pick now than to discover the plan came out the wrong shape.

Read `ticket-types/{type}.md` once the type is known. Its *"What this type is"* and *"What refine must establish"* sections are what Step 5 seeds from.

### Step 4 — Derive the slug, file it, and create the ticket

The slug is the ticket's id and its directory name. `ticket.py` derives it from the title when `--id` is absent.

Ask the front door where it would be filed, creating nothing:

```bash
python "{skills}/ticket-common/ticket.py" new --source {source} --title "<title>" --propose [--id {slug}] [--in namespace[/product]] [--context {context}]
```

Pass `--id` only for a slug the user chose.

- **Exit 0** → `id` is the slug; `product` and `filing` say where it would go and which rule chose it; `exists` says whether the slug is taken there; `elsewhere` lists a ticket of the same slug in another product. Show the qualified reference, the product and the filing reason, and ask whether to change the slug or the product — the user has to live with both, and each is a directory name. Where `exists` is true, the slug must change. Where `elsewhere` is not empty, say in one line that a bare reference to the slug will then need its product from outside the session context. Re-run `--propose` for anything the user changes; continue once they accept.
- **Exit 3** → more than one product could hold it and nothing prefers one. List the candidates from the hint, ask which, and re-run with `--in` set to the answer.
- **Exit 5** → the `--in` or the session context names a namespace or product that does not exist. Say so, and offer `/ticket-setup --in namespace[/product]` to create it rather than filing into a misspelling. Stop.
- **Any other non-zero exit** → report the message and its hint verbatim. Stop.

Read `ticket-providers/{source}/new.md` for what that store creates and where, then:

```bash
python "{skills}/ticket-common/ticket.py" new --source {source} --title "<title>" --id {slug} --type {type} --in "{product}" [--parent ref]
```

Always pass the confirmed slug with `--id` and the confirmed product with `--in`, so the ticket lands exactly where the user agreed. Include `--parent` only when the user supplied it; `new.md` says whether this source accepts it and what it validates.

If it exits non-zero, report the message and its hint verbatim and stop. A slug that already exists is the common case, and the fix is a different slug — never a merge into the existing directory. A `--parent` that does not resolve, or resolves to the wrong type, is also reported verbatim — never silently dropped or substituted.

### Step 5 — Seed the body from the type

The store created its own skeleton; `new.md` says what that skeleton is. Shape its stubs to the type by editing the ticket body the create step reported.

From `ticket-types/{type}.md`:

- Turn each thing *"What refine must establish"* names into a stub heading or a `TODO` line in the body, so the questions are visible in the file before the interview starts.
- Where *"What done means"* states an invariant that holds for this kind of work whether or not anyone wrote it down, put it in the acceptance section as a stated condition.

The point is that the ticket is born with the right shape: one kind of work starts with a question and a time-box already asked for, another starts with a stated "behaviour unchanged" condition, and the lightest kind starts with almost nothing — because that is what its type file says it needs.

Do not invent content. A seeded stub is a prompt for the refinement, not an answer to it, and it must read as one.

### Step 6 — Confirm and chain into refinement

Report in two lines at most: the qualified reference, title and type, with the path of the ticket body; and that the body was seeded from `ticket-types/{type}.md`, with acceptance criteria left as a `TODO` for refinement.

Then hand over to refinement, saying in the same line that it is experimental:

> Handing over to `/ticket-refine` — note it is **experimental** and still under development. Say "skip" to stop here and refine later.

Invoke the [`ticket-refine`](../ticket-refine/SKILL.md) skill, passing `{qualified_ref}`.

Chain by default: a ticket whose acceptance criteria are still a `TODO` stub is not ready to plan against, and refinement is what fills them in. But do not chain over an objection — the skill being handed to is experimental, so a user who wants to stop and read the seeded body first is making a reasonable call. If they skip, close by naming the two ways back in: `/ticket-refine {qualified_ref}` when they are ready, or editing the body by hand.
