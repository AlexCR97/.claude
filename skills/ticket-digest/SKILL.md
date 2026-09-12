---
name: ticket-digest
description: Reads a fetched ticket by reference, analyzes its description, acceptance criteria, attached files and images, and related tickets, then writes a structured digest to digest.md.
argument-hint: "<[source:]id> [--type T]"
allowed-tools: Read Grep Glob Write Bash(python:*)
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md` | everything specific to what shape the work is | only the **resolved** type's file |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

**`allowed-tools` is set on this skill deliberately.** It writes exactly one file, runs no build, touches no git, and makes no network call of its own — so an allowlist costs nothing and rules out a whole class of accident.

---

## Purpose

Turns a source-shaped snapshot into one readable document that every later skill works from. `digest.md` is the **single source of truth** for the ticket's content during planning and implementation — nothing downstream reads the raw snapshot again.

---

## Input

```
/ticket-digest <[source:]id> [--type {type}]
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

Everything below uses the paths, type and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `raw` requirement means there is nothing to digest yet; the hint names the skill that fixes it.

### 2. Read the two contracts this skill needs

**`ticket-providers/{source}/schema.md`** — where the content is on disk, the logical→physical field map, what markup the prose is in, how comments and attachments and related tickets are enumerated, and which logical fields this source simply does not have.

**`ticket-types/{type}.md`** — which sections matter for this kind of work, and which field to prefer when several could fill one. Read its *"What digest must surface"* section; the rest of the file belongs to other skills.

Where the type resolved to a fallback, the resolver's output says so. Mention it in one line when reporting, so a type that was guessed is never mistaken for one that was declared.

### 3. Extract the fields the Metadata table names

Using the field map in `schema.md`, read each logical field the digest template's Metadata table asks for. **Omit any row this source cannot fill** — the template's "omit any section that has no content" rule applies to rows as well, and an empty row invites a reader to think the value is missing rather than inapplicable.

Render the prose fields per the markup `schema.md` declares. Where it says HTML, strip the tags and decode the entities it names; where it says markdown or plain text, keep it as it is. Then **synthesize — do not copy verbatim into the digest**. The template says what each section should contain.

Where the type file names a field to prefer over another for this kind of work, prefer it. Where both are populated, they are different content and both matter.

### 4. Read the discussion

Enumerate and order the comments as `schema.md` describes. For each, extract:

1. **The plain text**, rendered per the declared markup.
2. **Mentions**, recognised the way `schema.md` says.
3. **Cross-references to other tickets**, recognised the way `schema.md` says. Note the referenced ids and cross-reference them against the related tickets already on disk — one is often already fetched in full.

### 5. Analyze the attachments and inline images

For each attachment the snapshot says was downloaded successfully, the file is under the ticket's `raw/` directory. **Use the on-disk name for the path and the display name for anything shown to a reader** — `schema.md` says which field is which, and they routinely differ, because a store that names every pasted screenshot the same thing has to rename them to keep them apart.

Read and analyze each file:

- **Image files** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`) — view visually and describe what is shown: an error screenshot, a UI mockup, a diagram, log output. Note where the image came from — which comment, or which field it was embedded in — using whatever the snapshot records for that.
- **Other files** (`.pdf`, `.docx`, `.txt`, `.md`, `.csv`, etc.) — read the content and summarize the relevant information.

Where an attachment failed to download, **note it as unavailable** rather than omitting it silently. A reader who cannot see a file is better served knowing it exists.

Where the type file says a particular kind of attachment is evidence rather than context — a trace, a log, a screenshot of the failure — describe what it shows rather than merely listing it.

### 6. Walk the related tickets

Walk the related tickets recursively as `schema.md` describes. For each node that was not skipped, extract its title, type and state. Group by relation kind.

A node that was skipped — because it was already visited, because the walk hit its depth limit, because the traversal policy excluded it, or because the call failed — **is listed as a reference by id only**, with no title. It has none; inventing one would be fabrication.

Where the source declares `capabilities.related` is false, omit the section entirely and say so in one line when reporting. That is a gap in what the source can express, not an empty result.

### 7. Write the digest

Read the template at `{skills}/ticket-digest/digest-template.md` and use it as the structure for the output file. Write it to the resolved `digest` path.

Rules:

- Omit any section — and any Metadata row — that has no content.
- Replace every `{placeholder}` with the actual value derived from the snapshot and the analysis.
- `{ticket-url}` is `ticket.json`'s `url`. **Where it is `null`, write the title as plain text rather than a broken link** — that source has no web address.
- For links to other tickets, comments and attachments, use the patterns in `ticket-providers/{source}/links.md`. It is a short file; read it rather than guessing a URL shape.
- **Always prefer the local downloaded file over a remote URL for an attachment.** `digest.md` sits in the ticket root, so a downloaded file is at `raw/{on-disk name}`. Fall back to the remote URL only where no local file exists.

Do not print the full digest body in chat. Once the file is written, confirm with a single line:

> Digest written to `{digest path}`

Add a second line only where something needs attention — a fallback type, a failed download, a capability the source lacks.

---

## Constraints

- Never modify, update, or close the ticket at its source
- Derive all content strictly from the fetched snapshot and the downloaded assets — **do not fabricate**
- Render prose per the markup the source declares; never assume a dialect
- Never name a field key in this file — the field map lives in the source's `schema.md`
- List a skipped related ticket by id only
- Note a failed attachment download as unavailable rather than omitting it
- Omit rather than invent a Metadata row the source cannot fill
- Do not print the digest body in chat
