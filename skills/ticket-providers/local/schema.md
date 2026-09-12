# local — schema

Read by `ticket-digest` and `ticket-refine`. Answers the six questions in `ticket-providers/README.md`.

## 1. Where the content lives

`{ticket-dir}/raw/ticket.md` — one markdown file, written and edited by hand. There is no API response and no snapshot: **this file is the ticket**, not a copy of one.

A small frontmatter block sits at the top, fenced by `---`, holding flat `key: value` pairs plus `[a, b]` lists. The rest is markdown under `##` headings.

## 2. The field map

| Logical field       | Physical location                                                                         |
| ------------------- | ----------------------------------------------------------------------------------------- |
| Id                  | the ticket directory's name — the slug                                                    |
| Native type         | frontmatter `type`                                                                        |
| Title               | frontmatter `title`, and the `#` heading, which mirror each other                         |
| State               | frontmatter `state`                                                                       |
| Description         | the `## Description` section                                                              |
| Acceptance criteria | the `## Acceptance Criteria` section                                                      |
| Labels              | frontmatter `labels`, a list                                                              |
| Reproduction steps  | *absent* — a bug's repro lives in `## Description`, or in a `##` section the author added |

**Fields this source does not have:** `Component`, `Milestone`, `Assignee`. There is no project structure, no iteration, and no assignment — one person's local notes have no one to assign to. **Omit those Metadata rows rather than filling them with a placeholder.**

**Unknown sections are carried through.** Any `##` heading that is not one of the four known ones is surfaced with its heading as its label. A user who adds `## Notes` or `## Prior art` must see it in the digest; silently dropping hand-written prose is the worst failure this store could have.

## 3. Markup

**Markdown**, throughout. No tags to strip, no entities to decode. Use the prose as written.

## 4. Comments, mentions and cross-references

The `## Comments` section. Each comment is a `###` sub-heading, newest last — appended in file order, which is chronological because nothing reorders them.

A refinement summary lands here as `### {timestamp} UTC — Refinement Session`.

| Concept         | How it is recognised                                                             |
| --------------- | -------------------------------------------------------------------------------- |
| Author          | *absent* — there is one author, the person whose machine this is                 |
| Mention         | ordinary markdown; nothing is structured, so treat an `@name` as plain text      |
| Cross-reference | a link in `## Links`, or an inline markdown link. There is no id syntax to parse |

## 5. Attachments

**Manual.** Any file the user has dropped into `{ticket-dir}/raw/` other than `ticket.md` is an attachment. There is no metadata record, no display-name-versus-on-disk-name distinction, and no download to fail: the file is either there or it is not.

List the directory to enumerate them. The on-disk name is also the display name.

## 6. Related tickets

**Absent.** `capabilities.related` is `false`: this store has no link structure, so there is no relation kind to enumerate and no tree to walk.

`## Links` may hold markdown links the author wrote, including to other local tickets. Treat them as prose, not as structured relations — surface them if they are useful, but they carry no type, state or title that can be trusted without opening the target.
