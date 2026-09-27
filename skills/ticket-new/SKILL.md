---
name: ticket-new
description: Creates a ticket in a store that supports it, seeded from its type so the body starts with the right questions, then chains into ticket-refine. For local tickets that have no upstream system to fetch from.
argument-hint: '"<title>" [--source S] [--type T] [--in NS[/PRODUCT]] [--parent REF]'
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file                                             |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

No `allowed-tools` here: this skill creates a ticket directory whose path is not known in advance.

---

## Purpose

Not all work arrives as a ticket in someone else's system. A refactor you decided on this morning, a spike you want to time-box before committing to an approach, a bug you found and will fix yourself — these deserve the same digest → plan → implement → checkpoint workflow, and none of them warrants creating an upstream ticket first.

This skill creates one locally, seeds its body from its **type** so it starts with the right questions rather than an empty template, and hands straight to refinement.

**It does not interview.** Establishing what the work actually is belongs to `/ticket-refine`, which this skill chains into. Acceptance criteria are left as an explicit `TODO` stub — a stub that says "refine this" is more honest than an invented criterion that later gets treated as a requirement.

---

## Input

```
/ticket-new "<title>" [--source {source}] [--type {type}] [--in {namespace}[/{product}]] [--parent {ref}]
```

- `{title}` — required. If none was given, ask for one before proceeding.
- `--source` — which store to create it in. When omitted, see step 2.
- `--type` — the kind of work. When omitted, see step 3.
- `--in` — the namespace or product to file it under. When omitted, see step 4. Namespace, product and filing mean what `ticket-common/GLOSSARY.md` says.
- `--parent` — for a task, the reference of the parent user story it belongs to. Optional, and only meaningful for a task; a source's `new.md` says whether it accepts this and how it is stored. When omitted for a task, leave it to the seeded stub from step 5 and to `/ticket-refine` to establish.

When this session has a session context, pass `--context {context}` on every `ticket.py` call below that takes one, and start your first output line with `Ticket context: {context}`. An `--in` in the invocation overrides it for that one call; say so in one line. `ticket-common/RESOLUTION.md` → _The session context_ has the rule.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Enumerate what is available

```bash
python "{skills}/ticket-common/ticket.py" sources
```

This gives the installed sources with their capabilities, and `known_types` — the list of ticket types. **Never assume a fixed set of either**; both are discovered by glob, and both grow by adding a file.

### 2. Resolve the source

Take the source the user supplied. If they supplied none, use the **only source whose `capabilities.new` is true**. Where more than one qualifies, list them and ask.

**Refuse a source that has no `new`:**

> `{source}` cannot create tickets — it is backed by a system whose tickets are created there, not here. Create it in that system and run `/ticket-fetch {source}:{id}` instead.

This is a **reported gap, not a fallback**. The absence of that source's `new.md` is documentation that creating an upstream ticket is out of scope, rather than something forgotten — do not improvise an API call, and do not silently create it locally instead. The front door refuses the verb for the same reason and with the same exit code.

### 3. Resolve the type

Take the type the user supplied. If they supplied none, **offer the list from step 1 and ask** — one line each, from the first paragraph of each type file. Do not default silently: type decides the shape of everything downstream, and it is much cheaper to pick now than to discover the plan came out the wrong shape.

Read `ticket-types/{type}.md` once the type is known. Its _"What this type is"_ and _"What refine must establish"_ sections are what step 5 seeds from.

### 4. Derive the slug, file it, and create the ticket

The slug is the ticket's id and its directory name. **The driver owns this algorithm** — it is a store convention, not a property of any source:

1. Lowercase the title.
2. Replace every run of non-alphanumeric characters with a single hyphen.
3. Trim leading and trailing hyphens.
4. Keep the **first 8 hyphen-separated words**, which is long enough to be recognisable in a directory listing and short enough to type.

`"Cache the authorization lookup"` → `cache-the-authorization-lookup`.

Then ask the front door where it would be filed, creating nothing:

```bash
python "{skills}/ticket-common/ticket.py" new --source {source} --title "{title}" --id {slug} --propose [--in {in}] [--context {context}]
```

`product` and `filing` say where it would go and which rule chose it; `exists` says whether that slug is already taken there, and `elsewhere` lists a ticket of the same slug in another product. **Exit 3** means more than one product could hold it and nothing prefers one: list the candidates from the hint and ask which. **Exit 5** means the `--in` or the session context names a namespace or product that does not exist: say so, and offer `/ticket-init --in {scope}` to create it rather than filing into a misspelling.

Show both the slug and the product, and let the user override either before creating anything — they have to live with both, and each is a directory name:

> Creating `{qualified_ref}` — filed under `{product}`: {filing reason}. Change the slug or the product?

Where `exists` is true, the slug needs changing. Where `elsewhere` is not empty, mention it in one line: a bare reference to the slug will then need its product to be unambiguous from outside the session context. Re-run `--propose` for anything the user changes.

Read `ticket-providers/{source}/new.md` for what that store creates and where, then:

```bash
python "{skills}/ticket-common/ticket.py" new --source {source} --title "{title}" --id {slug} --type {type} --in "{product}" [--parent {ref}]
```

Always pass the confirmed product with `--in`, so the ticket lands exactly where the user agreed. Include `--parent {ref}` only when the user supplied one; `new.md` says whether this source accepts it and what it validates.

If it exits non-zero, report the message and its hint verbatim and stop. A slug that already exists is the common case, and the fix is a different slug — never a merge into the existing directory. A `--parent` that does not resolve, or resolves to the wrong type, is also reported verbatim — never silently dropped or substituted.

### 5. Seed the body from the type

The store created its own skeleton; `new.md` says what that skeleton is. **Now shape its stubs to the type**, by editing the ticket body the create step reported.

From `ticket-types/{type}.md`:

- Turn each thing _"What refine must establish"_ names into a stub heading or a `TODO` line in the body, so the questions are visible in the file before the interview starts.
- Where _"What done means"_ states an invariant that holds for this kind of work whether or not anyone wrote it down, put it in the acceptance section as a stated condition.

The point is that the ticket is **born with the right shape**: one kind of work starts with a question and a time-box already asked for, another starts with a stated "behaviour unchanged" condition, and the lightest kind starts with almost nothing — because that is what its type file says it needs.

Do not invent content. A seeded stub is a prompt for the refinement, not an answer to it, and it must read as one.

### 6. Confirm and chain into refinement

Report in two lines at most:

> Created {qualified_ref} — {title} ({type}). Body at `{ticket file path}`.
> Seeded from `ticket-types/{type}.md`; acceptance criteria left as a TODO for refinement.

Then hand over to refinement, saying in the same line that it is experimental:

> Handing over to `/ticket-refine` — note it is **experimental** and still under development. Say "skip" to stop here and refine later.

```
Skill: ticket-refine
args: {qualified_ref}
```

Chain by default: a ticket whose acceptance criteria are still a `TODO` stub is not ready to plan against, and refinement is what fills them in. But do not chain over an objection — the skill being handed to is experimental, so a user who wants to stop and read the seeded body first is making a reasonable call. If they skip, close by naming the two ways back in: `/ticket-refine {qualified_ref}` when they are ready, or editing the body by hand.

---

## Constraints

- Never create a ticket in a source that declares it cannot: report the gap
- Never interview the user here — that is `/ticket-refine`'s job
- Never invent acceptance criteria; leave the stub and let refinement establish them
- Never invent content for a seeded section — a stub is a prompt, not an answer
- Never pick a type silently; ask, because it shapes every skill downstream
- Never create a ticket without showing the product it is filed under and letting the user change it
- Never write into an existing ticket directory — a collision is a different slug, never a merge
- Never write a file into the ticket directory other than what the store's `new.md` describes
