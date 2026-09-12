# ado — schema

Read by `ticket-digest` and `ticket-refine`. Answers the six questions in `ticket-providers/README.md`.

## 1. Where the content lives

`{ticket-dir}/raw/raw.json`. The root work item is at `tree.work_item`; its fields are at `tree.work_item.fields`. Every related work item repeats the same node shape under `tree.related[]`.

## 2. The field map

| Logical field | Physical key, under `tree.work_item.fields` |
| --- | --- |
| Id | `System.Id` |
| Native type | `System.WorkItemType` |
| Title | `System.Title` |
| State | `System.State` |
| Component | `System.AreaPath` |
| Milestone | `System.IterationPath` |
| Description | `System.Description` |
| Reproduction steps | `Microsoft.VSTS.TCM.ReproSteps` |
| Acceptance criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| Assignee | `System.AssignedTo.displayName` |
| Labels | `System.Tags` — semicolon-separated |
| Revision | `tree.work_item.rev` (not under `fields`) |

**Description vs reproduction steps.** Both exist as separate fields. Which one carries the content depends on the work item type — a Bug typically fills `Microsoft.VSTS.TCM.ReproSteps` and leaves `System.Description` empty, and the reverse for everything else. Read whichever is populated; where both are, they are different content and both matter.

**Nothing here is absent.** This source can fill every logical field.

**An identity field is an object, not a string.** `System.AssignedTo` and `System.ChangedBy` carry `displayName`, `uniqueName` and more. Read `displayName`.

## 3. Markup

**HTML.** `System.Description`, `Microsoft.VSTS.TCM.ReproSteps`, `Microsoft.VSTS.Common.AcceptanceCriteria` and every comment body are HTML fragments, not markdown and not plain text. Render them to plain text before writing anything derived from them.

Entities that appear routinely and must be decoded: `&nbsp;` `&amp;` `&lt;` `&gt;` `&quot;` `&#39;`.

## 4. Comments, mentions and cross-references

The thread is at `tree.discussion.comments`. **Sort by `createdDate` ascending** — the API order is not guaranteed to be chronological.

Each comment carries `id`, `text` (HTML), `createdBy` (an identity object), `createdDate` and `modifiedDate`.

| Concept | How it is recognised in the comment HTML |
| --- | --- |
| @mention | an `<a data-vss-mention>` element; the visible text is the display name |
| Cross-reference | an `<a href="…/_workitems/edit/{id}/">`, or a bare `#{number}` in the text |

Cross-referenced ids are worth checking against `tree.related`, which may already hold the full work item.

## 5. Attachments

`tree.attachments[]` on every node, each carrying:

| Key | Meaning |
| --- | --- |
| `source` | `relation`, `comment_inline_image`, or `field_inline:{field key}` |
| `name` | the original filename — **display only**, and it collides |
| `local_filename` | the on-disk name, or `null` when the download failed |
| `download_ok` | whether the file is actually present |
| `url` | the remote URL |
| `comment_id` | which comment it came from, where `source` is a comment |

**Always use `local_filename` for the path and `name` for anything shown to a reader** — never assume the two match. The file is at `{ticket-dir}/raw/{local_filename}`.

A failed download is signalled by `download_ok: false` with a null `local_filename`. It is noted as unavailable, never omitted.

## 6. Related tickets

`tree.related[]`, recursively. Each entry carries `relation_type` — one of `parent`, `child`, `related` — and then either a full node (with its own `work_item.fields`) or an id plus a `skipped_reason`.

| `skipped_reason` | Means |
| --- | --- |
| `traversal_policy` | this relation kind is not expanded for this root type |
| `already_visited` | it appears elsewhere in the tree |
| `max_depth_reached` | the walk stopped here |
| `fetch_failed` | the call errored; the error text is on the node |

A node with a `skipped_reason` has no title — it is a reference by id only.
