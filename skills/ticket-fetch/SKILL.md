---
name: ticket-fetch
description: Fetches or refreshes a ticket's raw data — fields, comments, attachments, related tickets — from its remote source into the ticket's raw/ directory. Required before ticket-refine or ticket-digest.
argument-hint: "<ref> [--in namespace[/product]]"
allowed-tools: Read Bash(python *ticket.py:*)
---

Downloads everything a remote source knows about a ticket into the ticket's `raw/` directory, so `ticket-refine` and `ticket-digest` work offline from one consistent snapshot. Run it again at any time to refresh the snapshot.

End state: a complete, fresh `raw/` and a refreshed `ticket.json`, plus a report of where the ticket is filed, any filing the fetch contradicts, any type note, and every attachment that failed to download.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill                                                        |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`<ref>`** — the ticket: a reference as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it, or the ticket's web address pasted verbatim. Step 1 turns every form into the same location, and no step parses an address. Ask for one when it is absent.
- **`[--in namespace[/product]]`** — where to file a ticket not yet on disk, overriding the filing rules. Namespace, product and filing mean what `ticket-common/GLOSSARY.md` says.

---

## Ground rules

1. **Never modify the ticket upstream.** Fetching is read-only, including every related ticket it walks.
2. **Keep attachment files already on disk.** The fetch downloads only what is new; never delete one.
3. **Report a missing capability or role file as a gap.** Never improvise a fetch, and never substitute another source's file for a missing one — `ticket-providers/README.md` → *Absence is the mechanism*.
4. **Never handle a credential.** Never print one, pass one to a command, or read one from a config.
5. **Stop on a non-zero exit.** The one exception is exit 3 on filing in Step 1, which asks and runs again.
6. **Move bytes, never read them.** Reading, summarizing or acting on the fetched content is `ticket-digest`'s job.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require config [--in namespace[/product]] [--context {context}]
```

- **Exit 0:** continue with the paths, capabilities, `ticket.json` and `qualified_ref` it returns. Every path is absolute. A ticket not on disk yet has `filed: false`, and `filing` names the product it will be filed under and the rule that chose it.
- **Exit 3 on filing:** more than one product can hold the ticket and nothing prefers one. List the candidates from the hint, ask which, and run this step again with `--in` set to the answer. Never pick one.
- **Any other non-zero exit:** report the message and its hint verbatim, and stop. An unmet `config` requirement means the source is not bound where the ticket is filed; the hint names the skill that binds it.

Open `ticket-common/RESOLUTION.md` only when the output is disputed.

### Step 2 — Refuse where the source cannot fetch

If `capabilities.fetch` is `false`, stop and report that `{source}` has no remote system to download from — its `raw/` is the original, not a copy.

This is a **reported gap, not a fallback**. Do not improvise a download, do not read another source's `fetch.md`, and do not treat the ticket's existing `raw/` as a failed fetch.

### Step 3 — Read the source's fetch contract

Read `ticket-providers/{source}/fetch.md`. It alone defines what lands in `raw/`, the traversal policy, the attachment rules, and what `ticket.json` is refreshed with.

These hold for every source, whatever `fetch.md` says. Report a `fetch.md` that relaxes one of them as a discrepancy:

- **Always re-download the raw snapshot.** A fetch that decided nothing had changed would defeat the point of running it.
- **Keep attachments already on disk; download only what is new.** Re-downloading a file that is already correct is wasted time and, worse, a window in which a good local copy is replaced by a failed one.
- **Abort rather than write a partial `raw/`.** A snapshot that is missing half its comments reads as complete to every later skill.
- **Never modify the ticket upstream.** Fetching is read-only, including any recursive walk.

### Step 4 — Run the fetch

```bash
python "{skills}/ticket-common/ticket.py" fetch "{qualified_ref}"
```

Pass Step 1's `qualified_ref`, so the fetch writes exactly where Step 1 said. For a pasted address, pass the address instead: its coordinates are what the fetch needs. Pass no credential flag — there is none.

On a non-zero exit, report its stderr and stop.

### Step 5 — Confirm

Report in one line which ticket was fetched and the `raw/` directory it was written to. Then report, from the fetch's own output:

- **Where a new ticket was filed**, when it was not on disk before: the product and the reason, from `filing`, in one line — `Filed under edwire/ew-educate: the only product ado is bound in.` Never silently. Where it is outside the session context, say that too.
- **A filing the fetch contradicts**, when the output carries `misfiled`: the ticket's own coordinates disagree with the product it is filed under. Name each disagreeing coordinate, and offer `/ticket-move {qualified_ref} {belongs_under}` — or, where `belongs_under` is null, say that no product is bound to its coordinates yet and `/ticket-setup` can bind one. Do not move it yourself.
- **The resolved type**, where the fetch reported a `type_note`: a tag overriding the native type, or a native type that mapped to nothing and fell back. Report it in one line. The mapping is in `ticket-providers/{source}/types.md`; what the type then *means* is `ticket-types/{type}.md`'s business, and neither is read here.
- **Every attachment that failed to download**, by name. Report it as unavailable; never omit it.
