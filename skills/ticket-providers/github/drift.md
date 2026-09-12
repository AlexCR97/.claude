# github — drift

Read by `ticket-resume`.

```
python "{skills}/ticket-common/ticket.py" drift {source}:{id}
```

Read-only against both GitHub and the local snapshot. The fetched data is never rewritten.

## Exit contract

| Exit | Means |
| --- | --- |
| 0 | the local copy is current |
| 1 | the comparison could not be made — nothing fetched yet, the CLI missing or signed out, no network |
| 2 | the issue changed since it was fetched |

## What is compared

The issue's **last-updated timestamp**, its **comment ids**, and these fields: `title`, `state`, `labels`, `body`.

## Two deliberate asymmetries

**The body reports *that* it changed, never *how*.** A rendered diff of a long markdown body belongs in the browser, not in a briefing.

**Labels are compared as a sorted set, not in order.** They get reordered freely, and a reordering is not a change. A label that was genuinely added or removed is worth surfacing, and on this source it matters more than elsewhere: a label is what decides the ticket's type, so a label change can mean the work is a different shape than the plan assumed.

## New comments

Any comment whose id is not in the local snapshot, oldest first, each with its author's login, its timestamp and a snippet capped at 400 characters — long enough to tell whether it answers an open question, short enough that the briefing stays readable. The full text is one re-fetch away.
