# ado — update

Read by `ticket-update`. Changing a work item writes to Azure DevOps, so it is **gated behind an explicit confirmation**, and **refused when the work item has changed upstream** since it was fetched.

## The flow

```
python "{skills}/ticket-common/ticket.py" update "{qualified_ref}" [flags] --propose
python "{skills}/ticket-common/ticket.py" update "{qualified_ref}" [flags] --confirm
```

1. **Drift check.** The front door runs this source's drift check first (`drift.md`). A stale snapshot exits 2 with the instruction to re-fetch, and writes nothing.
2. **Propose.** `--propose` reports `changes` — one `{field, before, after}` per field that differs — and writes nothing. Show every one as a before and after.
3. **Ask.** Require an explicit yes. Without `--confirm` the front door refuses to write, exiting 4.
4. **Write.** `--confirm` sends one JSON Patch (`application/json-patch+json`) carrying only the fields that changed.
5. **Re-fetch.** The snapshot is re-fetched, so `raw/` and `ticket.json` match upstream.

## The revision guards the write

The patch opens with `test /rev` against the revision in the snapshot. Azure DevOps applies a patch atomically, so if anyone edited the work item between the drift check and the write, the whole patch is rejected instead of overwriting their change. A rejection is reported verbatim: re-fetch and redo the update.

## What can change

| Field | Flag | Field written |
| --- | --- | --- |
| Title | `--title` | `System.Title` |
| Description | `--description-file` | `System.Description` — HTML |
| Acceptance criteria | `--criteria-file` | `Microsoft.VSTS.Common.AcceptanceCriteria` — HTML |
| State | `--state` | `System.State` — a state the work item's type allows; Azure DevOps refuses others |
| Tags | `--add-tag`, `--remove-tag` | `System.Tags`, `;`-separated. Repeatable; compared case-insensitively. A tag overrides the work item type when it names a spike or tech debt (`types.md`), so a tag change can change the type the next fetch records |

Comments are not changed here: they keep using `publish`. Assignee, iteration and area path are out of scope.
