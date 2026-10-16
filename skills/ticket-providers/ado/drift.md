# ado — drift

A **recipe**. Read by `ticket-resume`, `ticket-plan` and `ticket-digest`. The commands are examples, not an allowlist: use whatever `az` call reads what is needed.

**Read-only.** Nothing is written, upstream or in the ticket directory. `raw.json` is never rewritten.

## Compare the live work item with the snapshot

`{org}` and `{project}` are the `coordinates` the resolver reports. The snapshot is `raw/raw.json`: the revision at `tree.work_item.rev` (also `ticket.json`'s `fingerprint.rev`), the fields at `tree.work_item.fields`, and the comments at `tree.discussion.comments`.

```bash
az rest --method get --resource 499b84ac-1321-427f-aa17-267ca6975798 --url https://dev.azure.com/{org}/_apis/wit/workitems/{id} --url-parameters "fields=System.Title,System.State,System.ChangedDate,System.ChangedBy,System.AssignedTo,System.IterationPath,System.Tags,Microsoft.VSTS.Common.AcceptanceCriteria,System.Description" api-version=7.1

az rest --method get --resource 499b84ac-1321-427f-aa17-267ca6975798 --url https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{id}/comments --url-parameters api-version=7.1-preview.4
```

Keep `--method get` first, as written. Pass a URL's query through `--url-parameters`, never inside `--url`: the `&` in a query is read as a command separator by the shell that runs `az` on Windows. Percent-encode a project name that holds a space.

The work item is **stale** when any of these holds:

- its `rev` differs from the snapshot's;
- one of the tracked fields differs: `System.Title`, `System.State`, `System.AssignedTo`, `System.IterationPath`, `System.Tags`, `Microsoft.VSTS.Common.AcceptanceCriteria`, `System.Description`;
- a live comment's `id` is not among the snapshot's.

Everything else on a work item can move without altering what the developer should do next.

## Report

One of three verdicts, stated plainly:

- **Current** — nothing above differs. One line.
- **Changed** — each differing field as its name, what the snapshot held and what is live; each new comment with its author, date and a snippet capped at 400 characters, oldest first; and the revision, snapshot to live. Add who last changed it and how many days ago (`System.ChangedBy`, `System.ChangedDate`).
- **Could not be checked** — no snapshot on disk, the sign-in expired, or no network. Say which, and for a sign-in give the command `az` names. Never report a check that did not run as current.

## Two deliberate asymmetries

**HTML-bodied fields report *that* they changed, never *how*.** `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` are reported as a plain-text summary of about 80 characters on each side. A rendered diff of markup belongs in the browser, not in a briefing.

**`System.ChangedDate` and `System.ChangedBy` are context, not diff rows.** They move as a consequence of some other edit rather than being the edit. A row reading `ChangedBy: Ana → Bob` says who typed, not what changed, and the revision already reports that something did.

## An identity is an object

`System.AssignedTo` and `System.ChangedBy` carry `displayName`, `uniqueName` and more. Compare and show `displayName`.
