# local — new

Read by `ticket-new`. **This is the only source that has this file**, which is what makes `/ticket-new` refuse the remote ones.

## What gets created

```
{ticket-dir}/raw/ticket.md     the body — the source of truth for this store
{ticket-dir}/ticket.json       identity, with url: null
```

Nothing else. `digest.md`, `plan.md`, `journal.md` and `artifacts/` are each written by the skill that owns them, when it runs.

## The body's shape

`raw/ticket.md` is markdown with a small frontmatter block, created as:

```markdown
---
title: Cache the authorization lookup
type: task
state: New
created: 2026-09-11
labels: []
---

# Cache the authorization lookup

## Description

TODO — what is this, and why now?

## Acceptance Criteria

TODO — run `/ticket-refine` to establish these.

## Comments

## Links
```

**The frontmatter subset is deliberately tiny**: flat `key: value` pairs, plus `[a, b]` for a list. That is all the parser supports, and all it should — a store format that cannot be read without installing a YAML library is a store format that stops working.

**The four `##` headings are the contract**: `Description`, `Acceptance Criteria`, `Comments`, `Links`. Any other `##` section a user adds is carried through with its heading as a label, so nothing written by hand is silently dropped.

## Where the body goes under `raw/`

Not in the ticket root. Putting it under `raw/` means `--require raw` is satisfiable identically for every source, so the digest and refine drivers need no special case for a store with no fetch.

## Creating one

```
python "{skills}/ticket-common/ticket.py" new --source local --title "…" --id {slug} --type {type}
```

The **slug is the driver's** to derive — it is a store convention, not a property of this source. Passing `--id` is the normal path; omitting it falls back to a slug derived from the title.

## Seeding by type

The skeleton above is what this source creates. **Shaping the stubs to the ticket type is the driver's job**, done by editing `raw/ticket.md` afterwards — this file says what the store looks like, never what a type means.

Leave acceptance criteria as a `TODO` stub. Establishing them is refinement's work, and a stub that says so is more honest than an invented criterion.

## Attachments are manual

Nothing downloads. A user drops files into `{ticket-dir}/raw/` themselves, and they are picked up from there like any other attachment.
