---
name: ticket-refine
description: Interviews the user to challenge and sharpen a ticket's requirements — goal and success criteria, domain model and data, edge cases and failure modes — then posts the agreed Q&A summary back to the ticket. Experimental, under active development.
argument-hint: "<ref> [--type type]"
allowed-tools: Read Write Skill Bash(python *ticket.py:*)
---

Runs a structured interview with the user — goal and success criteria, domain model and data, edge cases and failure modes — to surface a ticket's ambiguities and resolve them before any planning or implementation, then posts the agreed summary back to the ticket.

**Experimental.** The interview's rounds, question sets, and how a type's required questions fold into them are still settling: expect it to need steering, and treat a round that asks what the ticket already answers, or misses what it should ask, as feedback worth stating. What it writes — the staged file, the summary's four sections — follows the suite's rules. It is the only ticket skill that writes to a system outside this machine, so Step 6's confirmation gate is load-bearing.

End state: the agreed summary posted to the ticket in the markup its source declares, the staged file removed by the post, and the snapshot refreshed where the source can fetch — or nothing posted, and the reason reported.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file                                             |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`<ref>`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Ask for one when it is absent.
- **`[--type type]`** — overrides the resolved type. Recorded in `ticket.json`, so a following skill inherits it with no flag.

---

## Ground rules

1. **Never post without an explicit yes.** Step 6's confirmation is the only gate between a half-formed summary and a comment other people read.
2. **Never read, search or explore a repository or project.** Base every question and recommendation on the ticket data alone — the snapshot, the discussion, the attachments, the related tickets. Discovering the workspace belongs to `ticket-plan`.
3. **Never modify source code, and never run a git operation.**
4. **Never handle a credential.** Never print one, pass one to a command, or read one from a config.
5. **Write the summary only in the markup the source declares.** A body in the wrong dialect arrives as escaped source rather than formatting.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require raw [--type type] [--context {context}]
```

Everything below uses the paths, capabilities, type and `ticket.json` it returns — and its `qualified_ref` wherever a later command names the ticket; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

### Step 2 — Read the two contracts this skill needs

**`ticket-providers/{source}/schema.md`** — the field map, the markup the prose is in, and how the discussion, attachments and related tickets are enumerated.

**`ticket-types/{type}.md`** — read its *"What refine must establish"* section. Those questions are **non-negotiable for this type** and are folded into the rounds below; the rest of the file belongs to other skills.

### Step 3 — Load the ticket context

Using the field map in `schema.md`, read the title, type, state, description, acceptance criteria — rendered per the declared markup — and also:

- **The discussion**, ordered as `schema.md` describes.
- **The attachments** that downloaded successfully: read each one, so the interview can reference it.
- **The related tickets** — titles and types, for domain context.

This combined context is the foundation for challenging the user's requirements.

### Step 4 — Conduct the refinement interview

Run a structured interview in three rounds. In each round, present all questions for that domain together, wait for the user's answers, then move to the next round. If any answer raises a follow-up question, ask it before advancing to the next round.

Fold the type's required questions into the rounds they belong to, alongside the standard ones below. A type file's questions are additions to this structure, never a replacement for it — and where a standard question is already answered by the ticket, say so and skip it rather than asking for what the ticket already says.

#### Question format

Number each question `N.M` — the round, then the question within it — and follow it with a quoted `Recommended:` line carrying the recommended answer, derived from the ticket context.

Example:

```
1.1 What is the single most important outcome this ticket must deliver?

> Recommended: Based on the acceptance criteria, the primary outcome is that a user can export their invoice history as a CSV file from the account portal.
```

After presenting all questions in a round, wait for the user's response before continuing. Accept partial answers — the user may skip questions they consider already clear, or override your recommendation.

#### Round 1 — Goal and success criteria

Cover:

- What is the single most important outcome this ticket must deliver?
- What does "done" look like from the end user's perspective?
- Are the acceptance criteria complete, or are there implicit expectations not captured?
- What would signal that this has failed in production?

#### Round 2 — Domain model and data

Cover:

- Which projects and repositories are involved in or affected by this ticket? (e.g. backends, frontends, APIs, databases, shared libraries, specific files or directories)
- Which domain entities are created, updated, deleted or involved in any way?
- Are there any new fields, relationships, or constraints being introduced to the data model?
- What invariants must always hold after this change? (e.g. uniqueness, foreign key integrity, business rules)
- Does this change affect any shared contracts (APIs, events, DTOs, database schemas) that other projects depend on?

#### Round 3 — Edge cases and failure modes

Cover:

- What happens if the input is invalid, missing, or malformed?
- What happens under concurrent access — can two users trigger conflicting operations simultaneously?
- What is the expected behavior if a downstream dependency (database, external API, message broker) is unavailable?
- Are there any rollback or compensating actions needed if this operation fails midway?
- Are there any security or authorization edge cases — users accessing data they should not, or privilege escalation paths?

#### Follow-up rounds

If any answer in rounds 1–3 surfaces a new ambiguity or dependency, open a follow-up round before closing the interview. Repeat until no open questions remain.

### Step 5 — Synthesize the refinement summary

Read `ticket-providers/{source}/publish.md`. It names the template to use, the markup to write it in, and where the summary lands.

Every source's template carries the same four sections in the same order — Goal and Success Criteria, Domain Model and Data, Edge Cases and Failure Modes, Open Items — because they mirror this skill's three rounds plus its unresolved-items rule. The markup varies with the destination; the structure is this file's.

Rules:

- Produce the markup `publish.md` names, not the one that feels natural. The dialect is a property of the destination's renderer: a body in the wrong one arrives as escaped source rather than formatting.
- Replace every `{placeholder}` with the actual value derived from the interview.
- Omit the Open Items section if everything was resolved.

### Step 6 — Show the preview and confirm

Print the full summary in chat and ask:

> Does this look correct? Reply "yes" to post it, or tell me what to change.

- **Changes requested** → update the summary, show the revised version, and ask again.
- **Declined** → post nothing. Stop.
- **Yes, and `capabilities.publish` is false** → stop and say so: the summary is written, but this source has nowhere to put it. That is a reported gap, not a reason to improvise a destination.
- **Yes** → continue to Step 7.

### Step 7 — Stage the comment file

Write the confirmed summary into the ticket directory, named `refinement-comment.{ext}` — where `{ext}` is the extension for the comment format the resolver reports. That is what stops a body being staged in a dialect the destination cannot render.

### Step 8 — Publish it

```bash
python "{skills}/ticket-common/ticket.py" publish "{qualified_ref}" --file "{staged file}" --delete-after-post
```

Pass no credential flag — there is none. `--delete-after-post` removes the staged file once the post is confirmed; do not delete it by hand, because if the post fails that file is what a retry uses.

On a non-zero exit, report its stderr and stop — **do not retry automatically**. A retry after an ambiguous failure is how a summary gets posted twice.

### Step 9 — Report the result

Report in one line that the refinement summary was posted to the ticket.

### Step 10 — Refresh the snapshot

The summary just posted changes the ticket's discussion, so the local snapshot is now stale.

**Only where the resolver reports `capabilities.fetch` is true**, invoke the [`ticket-fetch`](../ticket-fetch/SKILL.md) skill, passing `{qualified_ref}`. Do not ask for confirmation; this is a mandatory follow-up.

Once it completes, report that the updated discussion was pulled, and point at `/ticket-digest {qualified_ref}` as the next step.

Where the source cannot fetch, skip this entirely — the summary was written straight into the local store, so there is nothing to pull back. Say so in one line and point at the digest.
