# github — update

Read by `ticket-update`. Changing an issue writes to GitHub, so it is **gated behind an explicit confirmation**, and **refused when the issue has changed upstream** since it was fetched.

## The flow

```
python "{skills}/ticket-common/ticket.py" update "{qualified_ref}" [flags] --propose
python "{skills}/ticket-common/ticket.py" update "{qualified_ref}" [flags] --confirm
```

1. **Drift check.** The front door runs this source's drift check first (`drift.md`). A stale snapshot exits 2 with the instruction to re-fetch, and writes nothing: the diff is computed against the snapshot, and writing over an upstream edit would discard it.
2. **Propose.** `--propose` reports `changes` — one `{field, before, after}` per field that differs — and writes nothing. Show every one as a before and after.
3. **Ask.** Require an explicit yes. Without `--confirm` the front door refuses to write, exiting 4.
4. **Write.** `--confirm` sends one `PATCH` carrying only the fields that changed.
5. **Re-fetch.** The snapshot is re-fetched, so `raw/` and `ticket.json` match upstream.

## What can change

| Field | Flag | Notes |
| --- | --- | --- |
| Title | `--title` | |
| Description | `--description-file` | The part of the body before the acceptance criteria |
| Acceptance criteria | `--criteria-file` | The `## Acceptance Criteria` section of the body — an issue has no field for them (`schema.md`). Created at the end of the description when there is none |
| State | `--state open\|closed` | This source has only these two |
| Labels | `--add-label`, `--remove-label` | Repeatable; compared case-insensitively. A label decides the ticket's type (`types.md`), so a label change can change the type the next fetch records |

Whatever follows the acceptance criteria in the body is carried through untouched. Comments are not changed here: they are not changed by this skill.

Assignee, milestone and project are out of scope.
