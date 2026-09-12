---
name: ticket-fetch
description: Fetches raw ticket data (fields, comments, attachments, related tickets) from a remote source and writes it to the ticket's raw/ directory. Always re-fetches the snapshot; keeps existing attachment files and only downloads new ones. Required before running ticket-refine or ticket-digest.
argument-hint: "<[source:]id>"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md` | everything specific to what shape the work is | not read by this skill |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

No `allowed-tools` here: fetching writes a whole directory tree whose filenames are not known in advance.

---

## Purpose

Downloads everything the source knows about a ticket and stores it locally, so that `ticket-refine` and `ticket-digest` can work offline from a consistent snapshot. Run it any time you want to refresh the data.

**Fetch is for remote sources only.** A local store has no upstream to fetch from — its `raw/` *is* the source of truth, written by `/ticket-new` and edited by hand. That is not a special case in this skill; it falls out of step 2.

**Recommended skill order:**

```
ticket-init → ticket-fetch → ticket-refine → [fetch → refine → …] → ticket-digest → ticket-plan → ticket-implement
```

---

## Input

```
/ticket-fetch <[source:]id>
```

`{ref}` — the ticket, optionally prefixed with its source. If none is given, ask for one before proceeding.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the ticket

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require config
```

Everything below uses the paths, capabilities and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `config` requirement means the source was never initialized; the hint names the skill that fixes it.

### 2. Refuse where the source cannot fetch

If the resolver reports `capabilities.fetch` is **false**, stop:

> `{source}` has no fetch — it is not backed by a remote system, so there is nothing to download. Its `raw/` is already the source of truth.

This is a **reported gap, not a fallback**. Do not improvise a download, do not read another source's `fetch.md`, and do not treat the ticket's existing `raw/` as a failed fetch. The front door refuses the verb for the same reason and with the same exit code, so an attempt to run it anyway will simply be declined.

### 3. Read the source's fetch contract

Read `ticket-providers/{source}/fetch.md`. It is the only source of what lands in `raw/`, the traversal policy, the attachment rules, and what `ticket.json` is refreshed with.

Whatever it says, these hold for **every** source and are this skill's own contract — a `fetch.md` that appears to relax one of them is wrong, and the discrepancy is worth reporting:

- **Always re-download the raw snapshot.** A fetch that decided nothing had changed would defeat the point of running it.
- **Keep attachments already on disk; download only what is new.** Re-downloading a file that is already correct is wasted time and, worse, a window in which a good local copy is replaced by a failed one.
- **Abort rather than write a partial `raw/`.** A snapshot that is missing half its comments reads as complete to every later skill.
- **Never modify the ticket upstream.** Fetching is read-only, including any recursive walk.

### 4. Run the fetch

```bash
python "{skills}/ticket-common/ticket.py" fetch "{source}:{id}"
```

There is no credential flag — never pass one, and never read a credential out of a config yourself. The provider uses its cached credential and refreshes it when it is close to expiring.

Wait for it to complete. If it exits with a non-zero code, report the stderr output to the user and stop.

### 5. Confirm

Report the result in a single line, plus anything that needs attention:

> Fetched {ref} — raw data written to `{raw dir}`.

Then, from the fetch's own output:

- **The resolved type**, where the fetch reported a `type_note`. A tag overriding the native type, or a native type that mapped to nothing and fell back, is stated in one line — never silently. The mapping is in `ticket-providers/{source}/types.md`; what the type then *means* is `ticket-types/{type}.md`'s business, and neither is read here.
- **Any attachment that failed to download**, by name. It is noted as unavailable, never omitted.

---

## Constraints

- Never modify the ticket at its source
- Never delete existing attachment files — the fetch keeps files already on disk
- Never improvise a fetch for a source that declares it cannot: report the gap
- Never print a credential in chat, and never pass one to a command
- Do not proceed past a non-zero exit code
- Do not read, summarize, or act on the fetched content here — that is `ticket-digest`'s job. This skill moves bytes and reports what moved
