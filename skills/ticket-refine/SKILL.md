---
name: ticket-refine
description: EXPERIMENTAL — under active development, not extensively tested. Runs an interactive refinement session between Claude and the user to challenge and sharpen a ticket's requirements against its domain model and business context. Posts a structured Q&A summary back to the ticket when complete.
argument-hint: "<[source:]id> [--type T]"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md` | everything specific to what shape the work is | only the **resolved** type's file |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

No `allowed-tools` here: this skill stages a file and posts it, and the file's path is not known in advance.

---

## ⚠️ Experimental

**This skill is experimental and under active development.** It has not been extensively tested, and its structure is expected to keep changing — the round layout, the question sets, and how the type's required questions fold into them are all still settling.

Two consequences worth keeping in mind while it is in this state:

- **It is the only skill in the suite that writes to a system outside this machine.** Everything else reads. The confirmation gate in [step 6](#6-show-the-preview-and-confirm) is what stands between a half-formed summary and a comment other people will read, so treat that gate as load-bearing rather than a formality — **never post without an explicit yes**, and prefer a scratch ticket while trying the skill out.
- **Expect the interview to need steering.** Where a round asks something the ticket already answers, or misses something it should have asked, that is worth saying out loud — it is the feedback this skill is still being shaped by.

The steps below are the current design, not a settled contract. Everything the skill *writes* — the staged file, the summary's four sections — follows the same rules as the rest of the suite and is not experimental; it is the interview that is.

---

## Purpose

Raw tickets often under-specify what "done" looks like. This skill reads the fetched data and conducts a structured interview — covering goal and success criteria, domain model and data, and edge cases and failure modes — to surface ambiguities and resolve them before any planning or implementation begins. The agreed refinements are posted back to the ticket.

**Recommended skill order:**

```
ticket-init → ticket-fetch → ticket-refine → [fetch → refine → …] → ticket-digest → ticket-plan → ticket-implement
```

You may loop fetch and refine as the ticket evolves and its discussion grows.

---

## Input

```
/ticket-refine <[source:]id> [--type {type}]
```

- `{ref}` — the ticket, optionally prefixed with its source. If none is given, ask for one before proceeding.
- `--type` — override the resolved type. Recorded in `ticket.json`, so a following skill inherits it with no flag.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the ticket

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require raw [--type {type}]
```

Everything below uses the paths, capabilities, type and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

### 2. Read the two contracts this skill needs

**`ticket-providers/{source}/schema.md`** — the field map, the markup the prose is in, and how the discussion, attachments and related tickets are enumerated.

**`ticket-types/{type}.md`** — read its *"What refine must establish"* section. Those questions are **non-negotiable for this type** and are folded into the rounds below; the rest of the file belongs to other skills.

### 3. Load the ticket context

Using the field map in `schema.md`, read the title, type, state, description, acceptance criteria — rendered per the declared markup — and also:

- **The discussion**, ordered as `schema.md` describes.
- **The attachments** that downloaded successfully: read and internalize each one so you can reference it during the interview.
- **The related tickets** — titles and types, for domain context.

This combined context is the foundation for challenging the user's requirements.

### 4. Conduct the refinement interview

Run a structured interview in **three rounds**. In each round, present all questions for that domain together, wait for the user's answers, then move to the next round. If any answer raises a follow-up question, ask it before advancing to the next round.

**Fold the type's required questions into the rounds they belong to**, alongside the standard ones below. A type file's questions are additions to this structure, never a replacement for it — and where a standard question is already answered by the ticket, say so and skip it rather than asking for something you have.

#### Question format

Present each question in this format:

```
{N.M} {Question}

> Recommended: {your recommended answer, derived from the ticket context}
```

Where `N` is the round number and `M` is the question number within the round.

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

- Which services and projects are involved in or affected by this ticket? (e.g. files, folders, directories, backends, frontends, APIs, databases, shared libraries)
- Which domain entities are created, updated, deleted or involved in any way?
- Are there any new fields, relationships, or constraints being introduced to the data model?
- What invariants must always hold after this change? (e.g. uniqueness, foreign key integrity, business rules)
- Does this change affect any shared contracts (APIs, events, DTOs, database schemas) that other services depend on?

#### Round 3 — Edge cases and failure modes

Cover:

- What happens if the input is invalid, missing, or malformed?
- What happens under concurrent access — can two users trigger conflicting operations simultaneously?
- What is the expected behavior if a downstream dependency (database, external API, message broker) is unavailable?
- Are there any rollback or compensating actions needed if this operation fails midway?
- Are there any security or authorization edge cases — users accessing data they should not, or privilege escalation paths?

#### Follow-up rounds

If any answer in rounds 1–3 surfaces a new ambiguity or dependency, open a follow-up round before closing the interview. Repeat until no open questions remain.

### 5. Synthesize the refinement summary

Read `ticket-providers/{source}/publish.md`. It names the template to use, the markup to write it in, and where the summary lands.

Every source's template carries the **same four sections in the same order** — Goal and Success Criteria, Domain Model and Data, Edge Cases and Failure Modes, Open Items — because they mirror this skill's three rounds plus its unresolved-items rule. The markup varies with the destination; the structure is this file's.

Rules:

- **Produce the markup `publish.md` names, not the one that feels natural.** The dialect is a property of the destination's renderer: a body in the wrong one arrives as escaped source rather than formatting.
- Replace every `{placeholder}` with the actual value derived from the interview.
- Omit the Open Items section if everything was resolved.

### 6. Show the preview and confirm

Print the full summary in chat and ask:

> Does this look correct? Reply "yes" to post it, or tell me what to change.

Wait for the user's response. If they request changes, update the summary and show the revised version. Repeat until they confirm.

### 7. Stage the comment file

Write the confirmed summary into the ticket directory, named `refinement-comment.{ext}` — where `{ext}` is the extension for the comment format the resolver reports. That is what stops a body being staged in a dialect the destination cannot render.

### 8. Publish it

```bash
python "{skills}/ticket-common/ticket.py" publish "{source}:{id}" --file "{staged file}" --delete-after-post
```

There is no credential flag — never pass one, and never read a credential out of a config yourself. `--delete-after-post` removes the staged file once the post is confirmed; do not delete it by hand, because if the post fails that file is what a retry uses.

Wait for it to complete. If it exits with a non-zero code, report the stderr output and stop — **do not retry automatically**. A retry after an ambiguous failure is how a summary gets posted twice.

Where the resolver reports `capabilities.publish` is false, stop after step 6 and say so: the summary is written but this source has nowhere to put it. That is a reported gap, not a reason to improvise a destination.

### 9. Confirm

Report the result in a single line:

> Refinement summary posted to {ref}.

### 10. Refresh the snapshot

The summary just posted changes the ticket's discussion, so the local snapshot is now stale.

**Only where the resolver reports `capabilities.fetch` is true**, invoke the fetch skill for the same ticket — do not ask for confirmation, this is a mandatory follow-up:

```
Skill: ticket-fetch
args: {source}:{id}
```

Once it completes:

> Updated discussion pulled. Run `/ticket-digest {ref}` when you are ready to generate the digest.

Where the source cannot fetch, skip this entirely — the summary was written straight into the local store, so there is nothing to pull back. Say so in one line and point at the digest.

---

## Constraints

- Never modify source code files
- Never run git operations
- **Never read, search, or explore the codebase** — base all questions and recommendations solely on the ticket data: the snapshot, the discussion, the attachments, the related tickets. Codebase exploration is exclusive to `ticket-plan`
- Never post without the user's explicit confirmation in step 6
- Never print a credential in chat, and never pass one to a command
- Never write the summary in a markup dialect other than the one the source declares
- Do not delete the staged comment file manually — the publish verb deletes it once the post is confirmed
- Do not retry a failed post automatically
