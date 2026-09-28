---
name: ticket-digest
description: Reads a fetched ticket by reference, analyzes its description, acceptance criteria, attached files and images, and related tickets, then writes a structured digest to digest.md.
argument-hint: "<ref> [--type type]"
allowed-tools: Read Grep Glob Write Bash(python *ticket.py:*)
---

Turns a fetched, source-shaped snapshot into `digest.md`, the one readable document every later skill works from. `digest.md` is the single source of truth for the ticket's content during planning and implementation; nothing downstream reads the raw snapshot again.

End state: `digest.md` written at the resolved `digest` path from the snapshot alone, and a one-line confirmation, plus a line for any fallback type, failed download or capability the source lacks.

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

1. **Never modify the ticket upstream.** Never update or close it at its source.
2. **Never fabricate.** Derive all content from the fetched snapshot and the downloaded files.
3. **Render prose per the markup the source declares.** Never assume a dialect.
4. **Omit a Metadata row the source cannot fill.** An empty row reads as missing rather than inapplicable; never invent a value.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require raw [--type type] [--context {context}]
```

Everything below uses the paths, type and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `raw` requirement means there is nothing to digest yet; the hint names the skill that fixes it.

### Step 2 — Read the two contracts this skill needs

**`ticket-providers/{source}/schema.md`** — where the content is on disk, the logical→physical field map, what markup the prose is in, how comments and attachments and related tickets are enumerated, and which logical fields this source simply does not have.

**`ticket-types/{type}.md`** — which sections matter for this kind of work, and which field to prefer when several could fill one. Read its *"What digest must surface"* section; the rest of the file belongs to other skills.

Where the type resolved to a fallback, the resolver's output says so. Mention it in one line when reporting, so a type that was guessed is never mistaken for one that was declared.

### Step 3 — Extract the fields the Metadata table names

Using the field map in `schema.md`, read each logical field the digest template's Metadata table asks for. Omit any row this source cannot fill (ground rule 4).

Render the prose fields per the markup `schema.md` declares. Where it says HTML, strip the tags and decode the entities it names; where it says markdown or plain text, keep it as it is. Then synthesize — do not copy verbatim into the digest. The template says what each section should contain.

Where the type file names a field to prefer over another for this kind of work, prefer it. Where both are populated, they are different content and both matter.

### Step 4 — Read the discussion

Enumerate and order the comments as `schema.md` describes. For each, extract:

1. **The plain text**, rendered per the declared markup.
2. **Mentions**, recognised the way `schema.md` says.
3. **Cross-references to other tickets**, recognised the way `schema.md` says. Note the referenced ids and cross-reference them against the related tickets already on disk — one is often already fetched in full.

### Step 5 — Analyze the attachments and inline images

For each attachment the snapshot says was downloaded successfully, the file is under the ticket's `raw/` directory. Use the on-disk name for the path and the display name for anything shown to a reader — `schema.md` says which field is which, and they routinely differ, because a store that names every pasted screenshot the same thing has to rename them to keep them apart.

Read and analyze each file:

- **Image files** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`) — view visually and describe what is shown: an error screenshot, a UI mockup, a diagram, log output. Note where the image came from — which comment, or which field it was embedded in — using whatever the snapshot records for that.
- **Other files** (`.pdf`, `.docx`, `.txt`, `.md`, `.csv`, etc.) — read the content and summarize the relevant information.

Where an attachment failed to download, note it as unavailable rather than omitting it silently. A reader who cannot see a file is better served knowing it exists.

Where the type file says a particular kind of attachment is evidence rather than context — a trace, a log, a screenshot of the failure — describe what it shows rather than merely listing it.

### Step 6 — Walk the related tickets

Walk the related tickets recursively as `schema.md` describes. For each node that was not skipped, extract its title, type and state. Group by relation kind.

List a skipped node — one already visited, past the walk's depth limit, excluded by the traversal policy, or whose call failed — as a reference by id only, with no title. It has none; inventing one would be fabrication.

Where the source declares `capabilities.related` is false, omit the section entirely and say so in one line when reporting. That is a gap in what the source can express, not an empty result.

### Step 7 — Write the digest

Read [`digest-template.md`](./digest-template.md) and use it as the structure for the output file. Write it to the resolved `digest` path.

Rules:

- Omit any section — and any Metadata row — that has no content.
- Fill every `{camelCase}` placeholder with the value derived from the snapshot and the analysis, and replace every `<!-- guidance -->` comment with the content it asks for.
- `{ticketUrl}` is `ticket.json`'s `url`. Where it is `null`, write the title as plain text rather than a broken link — that source has no web address. `{relatedUrl}` follows `links.md`, below.
- `{assignee}` is `Unassigned`, and `{labels}` is `—`, when the source has none.
- For links to other tickets, comments and attachments, use the patterns in `ticket-providers/{source}/links.md`. It is a short file; read it rather than guessing a URL shape.
- Always prefer the local downloaded file over a remote URL for an attachment. `digest.md` sits in the ticket directory, so a downloaded file is at `raw/{on-disk name}`. Fall back to the remote URL only where no local file exists.

Do not print the full digest body in chat. Once the file is written, report in one line that the digest was written, with its path.

Add a second line only where something needs attention — a fallback type, a failed download, a capability the source lacks.
