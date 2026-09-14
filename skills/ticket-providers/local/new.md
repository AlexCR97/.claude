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
id: cache-the-authorization-lookup
title: Cache the authorization lookup
type: task
state: New
created: 2026-09-11T14:32:07+00:00
labels: []
parent: local:cache-invalidation-story
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

`id` mirrors the ticket directory's own name — the slug this driver derived or the caller passed via `--id`. It is written so `raw/ticket.md` is self-identifying even copied or read outside its directory; a mismatch between the two is a hand-editing mistake worth flagging, not a second source of truth to reconcile.

`created` is a full UTC timestamp — the same ISO 8601 shape as `ticket.json`'s `last_fetched_at` — not a bare date. Two tasks created minutes apart on the same day would otherwise be indistinguishable by `created` alone.

`parent` is written only when `--parent` was given — it is not part of the skeleton above. Omit the key entirely rather than writing it empty; an absent key and an empty value are not the same claim.

**The four `##` headings are the contract**: `Description`, `Acceptance Criteria`, `Comments`, `Links`. Any other `##` section a user adds is carried through with its heading as a label, so nothing written by hand is silently dropped.

## Where the body goes under `raw/`

Not in the ticket root. Putting it under `raw/` means `--require raw` is satisfiable identically for every source, so the digest and refine drivers need no special case for a store with no fetch.

## Creating one

```
python "{skills}/ticket-common/ticket.py" new --source local --title "…" --id {slug} --type {type} [--parent {ref}]
```

The **slug is the driver's** to derive — it is a store convention, not a property of this source. Passing `--id` is the normal path; omitting it falls back to a slug derived from the title.

## Linking a task to its parent user story

`--parent {ref}` is this source's own flag — the front door passes it through untouched. It records the optional task→user-story relationship `ticket-types/task.md` and `ticket-types/user-story.md` describe.

Rejected before anything is written:

- **`--parent` on anything but a task.** Only a task may have one; a user story (or any other type) with `--parent` set is refused.
- **A parent that is not on disk.** Create the parent user story first — this source never invents one.
- **A parent whose own `type` is not `user-story`.** The relationship this suite tracks is task-under-story, not task-under-anything.

Once accepted, the reference is written verbatim to frontmatter `parent` and to `ticket.json`, in `[source:]id` form — `local:cache-invalidation-story`, or a cross-source reference such as `ado:12345` where the parent lives elsewhere. There is no reverse index: a story's children are found by scanning, per `schema.md`.

A task created without `--parent` can still gain one later — a person edits `parent: {ref}` into the frontmatter by hand, exactly as every other field in this store is edited.

## Seeding by type

The skeleton above is what this source creates. **Shaping the stubs to the ticket type is the driver's job**, done by editing `raw/ticket.md` afterwards — this file says what the store looks like, never what a type means.

Wherever that editing mentions another local ticket — a parent, a prospective child, anything — write a real relative markdown link, never `[[double-bracket]]` wiki syntax. `schema.md`'s *"Writing a link to another local ticket"* has the exact path shape.

Leave acceptance criteria as a `TODO` stub. Establishing them is refinement's work, and a stub that says so is more honest than an invented criterion.

## Attachments are manual

Nothing downloads. A user drops files into `{ticket-dir}/raw/` themselves, and they are picked up from there like any other attachment.
