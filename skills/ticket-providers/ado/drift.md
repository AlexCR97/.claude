# ado — drift

Read by `ticket-resume`.

```
python "{skills}/ticket-common/ticket.py" drift {source}:{id}
```

Read-only against both Azure DevOps and the local data. `raw.json` is never rewritten.

## Exit contract

| Exit | Means |
| --- | --- |
| 0 | the local copy is current |
| 1 | the comparison could not be made — no raw data, expired `az login`, no network |
| 2 | the work item changed since it was fetched |

## What is compared

The work item's **revision** (`rev`, recorded as `ticket.json`'s fingerprint at fetch time), the **comment count and ids**, and these fields:

`System.Title`, `System.State`, `System.AssignedTo`, `System.IterationPath`, `System.Tags`, `Microsoft.VSTS.Common.AcceptanceCriteria`, `System.Description`.

Everything else on a work item can move without altering what the developer should do next.

## Two deliberate asymmetries

**HTML-bodied fields report *that* they changed, never *how*.** `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` are reported as a truncated plain-text summary on each side. A rendered diff of markup belongs in the browser, not in a briefing.

**`System.ChangedDate` and `System.ChangedBy` are context, not diff rows.** They move as a *consequence* of some other edit rather than being the edit. A row reading `ChangedBy: Ana → Bob` says who typed, not what changed, and the revision delta already reports that something did. They are surfaced as "changed by X, N days ago".

## New comments

Any comment whose id is not in the local snapshot, sorted oldest first, each with its author, date and a snippet capped at 400 characters — long enough to tell whether it answers an open question, short enough that the briefing stays readable. The full text is one re-fetch away.
