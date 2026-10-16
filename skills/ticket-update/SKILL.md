---
name: ticket-update
description: Changes an existing upstream ticket's title, description, acceptance criteria, state, or labels or tags, after showing a before and after and getting an explicit yes.
argument-hint: "<ref> [change]"
allowed-tools: Read Write Skill Bash(python *ticket.py:*) Bash(az boards:*) Bash(az rest:*) Bash(gh issue:*) Bash(gh api:*) Bash(gh label:*)
---

Changes an existing upstream ticket from the terminal: title, description, acceptance criteria, state, and labels or tags. It checks the ticket has not moved since it was fetched, shows exactly what would change, writes only on an explicit yes, and re-fetches so the local snapshot matches what is now upstream.

End state: the upstream ticket changed as the user confirmed and the local snapshot re-fetched to match — or nothing written, with the reason named.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in `ticket-providers/{source}/`: the source's `update.md` is a **recipe** for writing with the source's own CLI, and its `drift.md` for the check before it. Each step names the file to read.

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/` — never in this file.

---

## Parameters

- **`<ref>`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Ask for one when it is absent.
- **`[change]`** — in words. Step 3 turns it into the fields the source's `update.md` names.

---

## Ground rules

1. **Never write without an explicit yes.** The ticket is visible to everyone who can see the project, and an edit is hard to take back: show every change as a before and after first, and take only a plain yes.
2. **Never write over a drifted ticket.** The before and after are against the local snapshot, so first compare it with the live ticket as `drift.md` says. If upstream moved, say what moved and stop; re-fetch, then redo the update against what is there now. Where `update.md` names a revision guard, send it with the write.
3. **Report a missing capability as a gap.** A source that declares no `update` is refused. Never improvise a write another way, and never edit the local files as though that changed the ticket.
4. **Comments are not updated here.** No skill posts one.
5. **Change only what was asked.** Every field not named stays exactly as it is.
6. **Never print or read a token.** The source's CLI holds the sign-in and attaches it. When a call fails because the sign-in has expired, report that and the command it names.

---

## Execution Steps

### Step 1 — Resolve the ticket and the capability

With a session context, pass `--context {context}` on every `ticket.py` call below that takes one and open the first output line with `Ticket context: {context}`.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require raw [--context {context}]
```

On a non-zero exit, report the message and its hint verbatim and stop. If `capabilities.update` is false in the output, refuse: report that `{source}` cannot update tickets, and that its tickets are changed in the system that backs them. Stop.

Read `ticket-providers/{source}/update.md`. It says how each field is written, what markup the prose is in, and what guards the write. Its commands are examples: use whichever calls the change needs.

### Step 2 — Check the ticket has not moved

Read `ticket-providers/{source}/drift.md` and follow it. It compares the live ticket with the local snapshot and ends in a verdict.

- **Current** → continue.
- **Changed** → say what moved (the field changes and any new comments), tell the user to run `/ticket-fetch {qualified_ref}`, and stop. Do not offer to update anyway.
- **Could not be checked** → say why and stop: a write over a ticket that could not be compared is a write over a ticket that may have moved.

### Step 3 — Build the change

Turn the user's words into the fields `update.md` names. Where a description or acceptance criteria are changing, write the new text to a scratch file outside the ticket directory — the system temp directory — in the markup `update.md` names, and write any request body there too. Never invent text the user did not give; ask for it.

Take what each field holds now from the live read Step 2 made, or from `raw/` where the snapshot is the only record. Where a field is a combined value — a list of tags held in one string, a body holding several sections — build its new value from the whole of its current one, so nothing the user did not name is lost.

### Step 4 — Show the before and after

Show every field that would change as the field, what it is now, and what it would become, so a long body is compared and not just announced. Where nothing would change, say so and stop.

### Step 5 — Ask, then write

Ask for an explicit yes to exactly those changes. Anything short of a plain yes — silence, "maybe", a question — is not one; answer the question and ask again. On a no, change nothing and say so.

On a yes, write as `update.md` says, with its revision guard where it names one. Read the response, and compare what was stored with what the user confirmed. A rejection by the guard means the ticket moved after Step 2: report it verbatim and stop, as in Step 2.

### Step 6 — Re-fetch and report

```bash
python "{skills}/ticket-common/ticket.py" fetch "{qualified_ref}" [--context {context}]
```

So the snapshot, `ticket.json` and the raw data match upstream. On a non-zero exit, report the message and its hint verbatim.

Report in two lines at most: the ticket and each field changed, and that the snapshot was re-fetched. If the digest or plan were built from the old snapshot, say so, and point at `/ticket-digest {qualified_ref}` to bring the digest up to date.
