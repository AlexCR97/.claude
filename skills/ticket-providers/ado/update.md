# ado — update

A **recipe**. Read by `ticket-update`. Changing a work item writes to Azure DevOps, and the skill's own gates apply first: the drift check (`drift.md`), a before and after, and an explicit yes. This file is only how to write. The commands are examples, not an allowlist: use whatever `az` call the change needs.

`{org}` and `{project}` are the `coordinates` the resolver reports. Always pass them explicitly (`--org https://dev.azure.com/{org}`, `--project "{project}"`); never rely on a default set with `az devops configure`.

## What can change

| Field               | Field written                                                                     |
| ------------------- | --------------------------------------------------------------------------------- |
| Title               | `System.Title`                                                                    |
| Description         | `System.Description` — HTML                                                       |
| Acceptance criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` — HTML                                 |
| State               | `System.State` — a state the work item's type allows; Azure DevOps refuses others |
| Tags                | `System.Tags` — one `;`-separated string, see [Tags](#tags)                       |

Comments are not changed here. Assignee, iteration and area path are out of scope.

## The default: a JSON Patch, guarded by the revision

```bash
az rest --method patch --resource 499b84ac-1321-427f-aa17-267ca6975798 --url https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{id} --url-parameters api-version=7.1 --headers "Content-Type=application/json-patch+json" --body @{patch-file}
```

Write the patch to a scratch file outside the ticket directory. It is a JSON array of operations and **it opens with `test /rev`**, against the revision in the snapshot (`raw/raw.json` → `tree.work_item.rev`):

```json
[
  { "op": "test", "path": "/rev", "value": 28 },
  { "op": "add", "path": "/fields/System.Title", "value": "New title" },
  { "op": "add", "path": "/fields/System.Tags", "value": "api; spike" }
]
```

Azure DevOps applies a patch atomically. If anyone edited the work item since the snapshot, the `test` fails and the **whole patch is rejected** (`Precondition Failed`, `Test Operation for path /rev failed`) instead of overwriting their change. Report the rejection verbatim and say to re-fetch and redo the update; never retry with the revision changed. `add` replaces a field that already has a value.

Put every field of the change in **one** patch, so it lands whole or not at all. A response carries the work item as it now is, including the new `rev` and `fields`: show the changed fields from it.

## A simple edit

For one plain field, `az boards` is shorter, but it has no revision guard, so run the drift check immediately before it:

```bash
az boards work-item update --id {id} --org https://dev.azure.com/{org} --project "{project}" --title "New title" --state "Active"
```

Use the patch above instead for HTML bodies, tags, and any change of more than one field.

## Tags

`System.Tags` is **one string, `;`-separated**, not a list. There is no "add tag" call: writing the field replaces every tag, so a blind append loses the rest. Always:

1. Read the current value from the live work item (the drift check's response carries it), not from memory.
2. Split on `;` and trim each entry; drop empty ones.
3. Compare **case-insensitively**. Adding a tag that is already there changes nothing. Removing one removes every entry that matches, whatever its casing.
4. Keep the entries that stay in their order and casing; append an added tag as the user wrote it.
5. Join with a semicolon and a space and write the whole string in the patch. When the result is empty, use `{ "op": "remove", "path": "/fields/System.Tags" }` instead of an empty string.
6. Show the user the list before and after, and read `fields["System.Tags"]` in the response to confirm what was stored.

A tag can decide the ticket's type: a spike or tech-debt tag overrides the work item type (`types.md`), so a tag change can change the type the next fetch records. Say so when a requested tag is one of those.

## Markup

The description and acceptance criteria are HTML (`schema.md`). Write them as HTML fragments; do not send markdown.
