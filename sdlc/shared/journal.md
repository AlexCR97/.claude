# Journal

The format of a ticket's journal (`journal/`) and of its pull request record (`pulls.md`). Written only by `checkpoint`; `resume` reads the latest entry. Terms are in [`GLOSSARY.md`](../GLOSSARY.md).

## Entry file

- **Name:** `journal/{YYYY-MM-DD}T{HH-MM-SS}Z.md`, the UTC time the entry is written, with `-` where a clock has `:`. The names sort in time order. Read the clock in UTC (`date -u +%Y-%m-%dT%H-%M-%SZ`, or `(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ssZ")`).
- **Created once, never edited or deleted.** Before writing, list `journal/` and confirm the name is free; when it is taken, use the next free second. A correction is a new entry that says what it corrects.
- **The latest entry stands alone.** It carries forward every question and blocker still open from the previous one. An item is dropped only when this session resolved it, and the entry says how under Decisions.
- **No ticket location inside an entry.** The directory is the record of where a ticket is filed, and a stored location goes stale. A reference to another ticket is short within this ticket's product and qualified across products.

## Entry

````markdown
# Journal entry - [{reference}: {title}]({url or raw/ticket.md})

## {YYYY-MM-DD HH:MM} UTC - {stage}

**Where:** `{repository}` @ `{branch}` in `{worktree path}` - HEAD `{sha}` ({subject}), base `{base branch}` @ `{sha}`

**Worktree state:** {clean | N modified, N untracked - uncommitted}{, N stashes}

**Stopped at:** {the step and its honest state: what works, what does not, what is half-done}

**Next:** {the single next action: a file and an action}

### Done

- {what changed, as outcomes and not attempts; say where a change is uncommitted}

### Decisions

- **{decision}** - {why, and what it was chosen over}. Affects {step}.

### Inferences

- **{what the plan left unspecified}** - {what was assumed, and on what basis}. Affects {step}.

### Open questions

- {a question still open, and who or what can answer it}

### Blockers

- {a blocker still open, and what would clear it}
````

- **Stage** is `Phase N, Step N.M`, or `Planning`, `Refinement` or `Review`.
- **Where, Worktree state, Stopped at and Next are always present.** Where a fact is unavailable, say so; outside a repository, `**Where:** not in a repository`. When the work spans several worktrees, write one Where and one Worktree state per worktree, each naming its repository.
- **Next is specific enough to start on without re-reading anything**: never a bare "Continue Phase 2". When nothing is pending: `Nothing pending; all phases complete. Awaiting review.`
- **Omit an empty Done, Decisions, Inferences, Open questions or Blockers section.**
- **Decisions and Inferences stated earlier in the session**, such as an `implement` run's report, are carried over verbatim: that report is their only record.

## Pull request record

`pulls.md` in the ticket directory. Unlike an entry, it is rewritten in full on each refresh.

```markdown
# Pull requests

Status as of {YYYY-MM-DD HH:MM} UTC.

- [{label}]({url}) - {status}
```

- **A record with no pull request yet** has the line `No pull requests deliver this ticket yet.` in place of the list.
- **One line per pull request that delivers this ticket's work**, linked by its URL. The label is `{owner}/{repository}#{number}` for GitHub and `{project}/{repository}!{number}` for Azure DevOps.
- **The status** is the host's own: `draft`, `open`, `merged` or `closed`, then optionally the checks (`checks passing`, `checks failing`, `checks pending`) and the review state (`approved`, `changes requested`, `waiting for author`, `rejected`), comma-separated.
- **The time is the time of the refresh** and covers every line: refresh all statuses together. When a refresh fails, keep the previous statuses and time and add the line `Refresh failed: {reason}.`
- **A pull request that delivers two tickets is in both records**; a record knows nothing of another ticket.
- **A pull request belongs to the ticket** when it was opened for it in the session, the user said so, or its head is a branch the plan's Workspace section lists. A branch whose name resembles the ticket is never enough.
