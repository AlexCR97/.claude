# ado — new

Read by `ticket-create`. Creating a work item writes to Azure DevOps, so it is **gated behind an explicit confirmation**: it outlives the session and is visible to everyone on the project.

## The flow

1. **Propose.** Nothing is written; the project's work item types are read so the native type is the project's own.

   ```
   python "{skills}/ticket-common/ticket.py" new --source ado --title "…" --type {type} [--body-file F] [--criteria-file F] [--tag T ...] [--parent {id}] --propose [--in {namespace}/{product}]
   ```

   It reports the product it would be filed under and a `proposal`: the organization and project, title, canonical `type` and the `native_type` it would be created as, the tags (`labels`), the `body`, the `acceptance_criteria` and the `parent`. Show **all** of it, and let the user correct any of it. Re-run `--propose` for each correction.

2. **Ask.** Require an explicit yes. Without `--confirm` the front door refuses to write, exiting 4.

3. **Create.** Re-run with `--confirm` in place of `--propose`. It creates the work item, **fetches it immediately**, and files it under the id Azure DevOps assigned. The report carries `created`, `fetched` and `ticket_json`.

4. **Chain into refinement**, as for a local ticket.

## What is sent

| Field | Sent as |
| --- | --- |
| Title | `System.Title` |
| Description | `System.Description` — `--body-file`, HTML |
| Acceptance criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` — `--criteria-file`, HTML |
| Tags | `System.Tags`, `;`-separated — `--tag`, repeatable, plus the type's tag |
| Parent | a `System.LinkTypes.Hierarchy-Reverse` relation to `--parent` |

The request is a JSON Patch document (`application/json-patch+json`) to `…/_apis/wit/workitems/${native type}`.

## The native type

Read from the project, not hardcoded: `GET …/_apis/wit/workitemtypes` lists what its process template has, and the first candidate in `types.md` → *Creating: canonical to native* that the project has is used. A project with none of them is an error that lists the types it does have.

## A parent

`--parent` is accepted for a **task** only, as an id or `ado:{id}`. It is linked upstream, and recorded in `ticket.json` as `parent: ado:{id}` so the link exists locally the moment the ticket is filed. A parent on any other type is refused before anything is written.

Assignee, iteration and area path are out of scope.
