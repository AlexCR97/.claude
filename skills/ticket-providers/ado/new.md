# ado — new

A **recipe**. Read by `ticket-create`. Creating a work item writes to Azure DevOps, and it outlives the session and is visible to everyone on the project, so the skill's own gate applies first: show everything, and take an explicit yes. This file is only how to build and send it. The commands are examples, not an allowlist: use whatever `az` call the work needs.

`{org}` and `{project}` are the `coordinates` the resolver reports for the product the ticket will be filed under. Pass them explicitly; never rely on a default set with `az devops configure`.

## What is sent

| Field               | Sent as                                                             |
| ------------------- | ------------------------------------------------------------------- |
| Title               | `System.Title`                                                      |
| Description         | `System.Description` — HTML                                         |
| Acceptance criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` — HTML                   |
| Tags                | `System.Tags`, `;`-separated, including the type's tag (`types.md`) |
| Parent              | a `System.LinkTypes.Hierarchy-Reverse` relation to the parent's id  |

Assignee, iteration and area path are out of scope.

## 1. The native type

Read from the project, not hardcoded. Process templates name them differently — Agile calls a story "User Story", Scrum "Product Backlog Item":

```bash
az rest --method get --resource 499b84ac-1321-427f-aa17-267ca6975798 --url https://dev.azure.com/{org}/{project}/_apis/wit/workitemtypes --url-parameters api-version=7.1 --query "value[].name" --output tsv
```

Take the first candidate for the canonical type in `types.md` → *Creating: canonical to native* that the project has. A project with none of them is an error that lists the types it does have. Spike and tech debt are created as a task and told apart by their tag.

## 2. A parent

Accepted for a **task** only, as an id or `ado:{id}`. Refuse a parent on any other type before anything is written.

## 3. Show it all, and take a yes

Show the product it will be filed under, the organization and project, the title, the type and the native type it will be created as, the tags, the body, the acceptance criteria and the parent. Let the user correct any of it; show it again after each correction. Only a plain yes is a yes.

## 4. Create

A JSON Patch with one `add` per field sent, posted to the type's endpoint, in a scratch file outside the ticket directory:

```bash
az rest --method post --resource 499b84ac-1321-427f-aa17-267ca6975798 --url "https://dev.azure.com/{org}/{project}/_apis/wit/workitems/${native type}" --url-parameters api-version=7.1 --headers "Content-Type=application/json-patch+json" --body @{patch-file}
```

```json
[
  { "op": "add", "path": "/fields/System.Title", "value": "…" },
  { "op": "add", "path": "/fields/System.Description", "value": "<p>…</p>" },
  { "op": "add", "path": "/fields/System.Tags", "value": "spike" },
  {
    "op": "add",
    "path": "/relations/-",
    "value": { "rel": "System.LinkTypes.Hierarchy-Reverse", "url": "https://dev.azure.com/{org}/_apis/wit/workItems/{parent id}" }
  }
]
```

A native type with a space is percent-encoded in the URL (`User%20Story`). For a work item with no parent, tags or HTML, `az boards work-item create --type "{native type}" --title "…" --org https://dev.azure.com/{org} --project "{project}"` does it in one call. The response carries the new `id`.

## 5. File it

The id is only known now, so the work item is fetched and filed like any other, with the same coordinates:

```bash
python "{skills}/ticket-common/ticket.py" fetch ado:{id} --in {namespace}/{product}
```

Then:

- Where the fetch's `type` is not the type that was asked for, run `ticket.py resolve ado:{id} --type {type}`, which records it.
- For a parent, add `"parent": "ado:{parent id}"` to the ticket's `ticket.json`, leaving every other key as it is, so the link exists locally the moment the ticket is filed.
