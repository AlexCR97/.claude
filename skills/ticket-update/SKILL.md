---
name: ticket-update
description: Changes an existing upstream ticket's title, description, acceptance criteria, state, or labels or tags, after showing a before and after and getting an explicit yes.
argument-hint: "<ref> [change]"
allowed-tools: Read Write Skill Bash(python *ticket.py:*)
---

Changes an existing upstream ticket from the terminal: title, description, acceptance criteria, state, and labels or tags. It checks the ticket has not moved since it was fetched, shows exactly what would change, writes only on an explicit yes, and re-fetches so the local snapshot matches what is now upstream.

End state: the upstream ticket changed as the user confirmed and the local snapshot re-fetched to match — or nothing written, with the reason named.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in `ticket-providers/{source}/`, and each step names the file to read.

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/` — never in this file.

---

## Parameters

- **`<ref>`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Ask for one when it is absent.
- **`[change]`** — in words. Step 3 turns it into the source's flags.

---

## Ground rules

1. **Never write without an explicit yes.** The ticket is visible to everyone who can see the project, and an edit is hard to take back: show every change as a before and after first, and take only a plain yes.
2. **Never write over a drifted ticket.** The diff is against the local snapshot; if upstream moved, the front door refuses and says to re-fetch. Do not work around it — re-fetch, then redo the update against what is there now.
3. **Report a missing capability as a gap.** A source that declares no `update` is refused. Never improvise an API call, and never edit the local files as though that changed the ticket.
4. **Comments are not updated here.** Posting one keeps using `ticket-refine`'s publish path.
5. **Change only what was asked.** Every field not named stays exactly as it is.

---

## Execution Steps

### Step 1 — Resolve the ticket and the capability

With a session context, pass `--context {context}` on every `ticket.py` call below that takes one and open the first output line with `Ticket context: {context}`.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require raw [--context {context}]
```

On a non-zero exit, report the message and its hint verbatim and stop. If `capabilities.update` is false in the output, refuse: report that `{source}` cannot update tickets, and that its tickets are changed in the system that backs them. Stop.

Read `ticket-providers/{source}/update.md`. It names the flags, what each field means in that source, and its markup.

### Step 2 — Check the ticket has not moved

```bash
python "{skills}/ticket-common/ticket.py" drift "{qualified_ref}"
```

Exit `2` means it changed upstream: say what moved (`field_changes`, new comments), tell the user to run `/ticket-fetch {qualified_ref}`, and stop. Do not offer to update anyway.

### Step 3 — Build the change

Turn the user's words into the source's flags from `update.md`. Where a description or acceptance criteria are changing, write the new text to a scratch file outside the ticket directory — the system temp directory — in the markup `update.md` names, and pass it by file. Never invent text the user did not give; ask for it.

### Step 4 — Show the before and after

```bash
python "{skills}/ticket-common/ticket.py" update "{qualified_ref}" {flags} --propose
```

Show every entry of `changes` as the field, what it is now, and what it would become, so a long body is compared and not just announced. If `changes` is empty, say nothing would change and stop.

### Step 5 — Ask, then write

Ask for an explicit yes to exactly those changes. Anything short of a plain yes — silence, "maybe", a question — is not one; answer the question and ask again. On a no, change nothing and say so.

On a yes, re-run the same command with `--confirm` in place of `--propose`.

### Step 6 — Report

The write is followed by a re-fetch, so the snapshot, `ticket.json` and the raw data now match upstream. Report in two lines at most: the ticket and each field changed, and that the snapshot was re-fetched. If the digest or plan were built from the old snapshot, say so, and point at `/ticket-digest {qualified_ref}` to bring the digest up to date.
