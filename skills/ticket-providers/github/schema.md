# github — schema

Read by `ticket-digest` and `ticket-refine`. Answers the six questions in `ticket-providers/README.md`.

## 1. Where the content lives

`{ticket-dir}/raw/raw.json`. The issue is at `issue`; the comment thread is the flat array at `comments`. There is no tree — this source has no related-ticket structure to nest.

## 2. The field map

| Logical field | Physical key |
| --- | --- |
| Id | `issue.number` |
| Title | `issue.title` |
| State | `issue.state` — `open` or `closed` |
| Description | `issue.body` |
| Labels | `issue.labels[].name` |
| Assignee | `issue.assignees[].login` — a list, possibly empty |
| Author | `issue.user.login` |
| Milestone | `issue.milestone.title` — often null |

**Fields this source does not have:** `Component`, a dedicated **acceptance criteria** field, and a dedicated **reproduction steps** field.

That last pair matters more than it looks. An issue body is one free-text field: acceptance criteria and repro steps are conventions people write *inside* it, usually under their own markdown heading. **Look for them as headings within `issue.body`** — `## Acceptance Criteria`, `### Steps to reproduce`, and the obvious variants — and where none exists, say the field is absent rather than distilling one out of the prose. A criterion the digest invented will be treated downstream as a requirement someone agreed to.

`state` is only ever `open` or `closed`. Do not map it onto a richer workflow vocabulary that this source does not have.

## 3. Markup

**Markdown** — GitHub Flavored. No tags to strip and no entities to decode.

Two constructs are worth preserving rather than flattening, because they carry meaning: **task lists** (`- [ ]` and `- [x]`) are frequently how acceptance criteria are written and tracked, and **fenced code blocks** are often the repro or the error itself.

## 4. Comments, mentions and cross-references

The `comments` array, already in chronological order as returned. Each carries `id`, `body` (markdown), `user.login`, `created_at` and `updated_at`.

| Concept | How it is recognised |
| --- | --- |
| Mention | an `@login` in the body text — plain markdown, not a structured element |
| Cross-reference | `#123` for an issue in the same repository, `owner/name#123` for another, or a full issue URL |

**A cross-reference cannot be resolved to a title here.** This source declares `capabilities.related` false, so no related data was fetched. Surface the reference as written; never present it as though the target's title or state were known.

## 5. Attachments

**Absent.** `capabilities.attachments` is `false`.

An uploaded file appears as a markdown link to a user-content URL inside a body or a comment, with no enumerable list and no reliable way to distinguish it from any other link. Nothing is downloaded.

Where a body links to what is clearly an image or a file, **mention it as a link and say it was not downloaded**. Do not describe what it shows — it was never fetched, and describing an image nobody looked at is fabrication.

## 6. Related tickets

**Absent.** `capabilities.related` is `false` — see `fetch.md` for why. Omit the section rather than presenting an empty one.
