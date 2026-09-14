# local — schema

Read by `ticket-digest` and `ticket-refine`. Answers the six questions in `ticket-providers/README.md`.

## 1. Where the content lives

`{ticket-dir}/raw/ticket.md` — one markdown file, written and edited by hand. There is no API response and no snapshot: **this file is the ticket**, not a copy of one.

A small frontmatter block sits at the top, fenced by `---`, holding flat `key: value` pairs plus `[a, b]` lists. The rest is markdown under `##` headings.

## 2. The field map

| Logical field       | Physical location                                                                         |
| ------------------- | ----------------------------------------------------------------------------------------- |
| Id                  | frontmatter `id`, and the ticket directory's name — the slug, which mirror each other     |
| Native type         | frontmatter `type`                                                                        |
| Title               | frontmatter `title`, and the `#` heading, which mirror each other                         |
| State               | frontmatter `state`                                                                       |
| Description         | the `## Description` section                                                              |
| Acceptance criteria | the `## Acceptance Criteria` section                                                      |
| Labels              | frontmatter `labels`, a list                                                              |
| Parent              | frontmatter `parent` — a `[source:]id` reference, present only on a task that has one     |
| Reproduction steps  | *absent* — a bug's repro lives in `## Description`, or in a `##` section the author added |

**Fields this source does not have:** `Component`, `Milestone`, `Assignee`. There is no project structure, no iteration, and no assignment — one person's local notes have no one to assign to. **Omit those Metadata rows rather than filling them with a placeholder.**

**Unknown sections are carried through.** Any `##` heading that is not one of the four known ones is surfaced with its heading as its label. A user who adds `## Notes` or `## Prior art` must see it in the digest; silently dropping hand-written prose is the worst failure this store could have.

## 3. Markup

**Markdown**, throughout. No tags to strip, no entities to decode. Use the prose as written.

## 4. Comments, mentions and cross-references

The `## Comments` section. Each comment is a `###` sub-heading, newest last — appended in file order, which is chronological because nothing reorders them. Hand-written only: `/ticket-refine` no longer posts here — see `publish.md` for where a refinement's conclusions land instead.

| Concept         | How it is recognized                                                                                                               |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Author          | *absent* — there is one author, the person whose machine this is                                                                   |
| Mention         | ordinary markdown; nothing is structured, so treat an `@name` as plain text                                                        |
| Cross-reference | a link in `## Links`, or an inline markdown link — see *"Writing a link to another local ticket"* in §6 for the shape it must take |

## 5. Attachments

**Manual.** Any file the user has dropped into `{ticket-dir}/raw/` other than `ticket.md` is an attachment. There is no metadata record, no display-name-versus-on-disk-name distinction, and no download to fail: the file is either there or it is not.

List the directory to enumerate them. The on-disk name is also the display name.

## 6. Related tickets

**One relation only: a task's link to its parent user story.** `capabilities.related` is `true`, but this store has no generic link structure and no tree — build both directions by reading frontmatter across tickets, not by calling anything.

| Direction | Where it comes from                                                                                                                                                                                                                                                                                 |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent    | frontmatter `parent` on this ticket — a `[source:]id` reference, present only when this ticket is a task that was given one. Always absent on a user story and on a standalone task.                                                                                                                |
| Children  | not stored on this ticket. Enumerate every local ticket under `{tickets_home}/local/*/raw/ticket.md`, read each one's frontmatter, and collect the ones whose `parent` resolves to this ticket's own `source:id`. Only meaningful when this ticket's type is `user-story` — a task has no children. |

Resolve a bare `parent` value (no `source:` prefix) as `local:{id}` — that is the only store it could have been written against. To render a Parent or Children entry, open that ticket's own `ticket.json` for its title, type and state; never fabricate them from the id alone. A `parent` naming a ticket that is not on disk is listed as a reference by id only, exactly like a skipped node elsewhere in this suite.

**No generic `related` kind exists here.** `## Links` may hold markdown links the author wrote, including to other local tickets. Treat them as prose, not as structured relations — surface them if they are useful, but they carry no type, state or title that can be trusted without opening the target.

### Writing a link to another local ticket

Whoever writes into this store — a driver seeding or refining a body, or a person editing by hand — links to another local ticket with a **real relative markdown link**, never `[[double-bracket]]` wiki syntax. This store has no wiki-link resolver; `[[id]]` renders as literal bracketed text in every markdown viewer that opens `raw/ticket.md`, including this one, which makes it a broken link, not a working one dressed differently.

Every ticket lives at `{tickets_home}/local/{id}/raw/ticket.md`, so from inside one ticket's `raw/ticket.md`, a sibling is always two levels up and back down:

```
[{other-id}](../../{other-id}/raw/ticket.md)
```

For example, from `local/fincaapp-google-play-compliance-requirements/raw/ticket.md`:

```
[author-and-publish-google-play-privacy-policy](../../author-and-publish-google-play-privacy-policy/raw/ticket.md)
```

Use the target's id as the link text unless the surrounding prose already names it more descriptively. This applies everywhere a local ticket is mentioned — `## Links`, the Description, a comment — not only to the `parent` relation.
