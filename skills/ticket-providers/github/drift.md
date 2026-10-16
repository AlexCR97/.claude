# github — drift

A **recipe**. Read by `ticket-resume`, `ticket-plan` and `ticket-digest`. The commands are examples, not an allowlist: use whatever `gh` call reads what is needed.

**Read-only.** Nothing is written, upstream or in the ticket directory. The fetched data is never rewritten.

## Compare the live issue with the snapshot

`{owner}` and `{repository}` are the `coordinates` the resolver reports. The snapshot is `raw/raw.json`: the issue at `issue` and the comments at `comments`; `ticket.json`'s `fingerprint` holds `updated_at` and `comment_count`.

```bash
gh api repos/{owner}/{repository}/issues/{number}
gh api repos/{owner}/{repository}/issues/{number}/comments --paginate
```

The issue is **stale** when any of these holds:

- its `updated_at` differs from the snapshot's;
- `title`, `state`, `body` or the set of labels differs;
- a live comment's `id` is not among the snapshot's.

## Report

One of three verdicts, stated plainly:

- **Current** — nothing above differs. One line.
- **Changed** — each differing field as its name, what the snapshot held and what is live; each new comment with its author's login, its timestamp and a snippet capped at 400 characters, oldest first; and the last-updated time, snapshot to live, with how many days ago the issue changed.
- **Could not be checked** — nothing fetched yet, `gh` missing or signed out, or no network. Say which, and for a sign-in give the command `gh` names. Never report a check that did not run as current.

## Two deliberate asymmetries

**The body reports *that* it changed, never *how*.** A rendered diff of a long markdown body belongs in the browser, not in a briefing.

**Labels are compared as a sorted set, not in order.** They get reordered freely, and a reordering is not a change. A label that was genuinely added or removed is worth surfacing, and on this source it matters more than elsewhere: a label is what decides the ticket's type, so a label change can mean the work is a different shape than the plan assumed.
