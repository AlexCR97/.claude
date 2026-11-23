# Journal

The format of a ticket's journal (`journal/`), of a journal entry posted upstream, and of the pull request record (`pulls.md`). Written and posted only by `checkpoint`, mirrored from upstream by `fetch`; `resume` reads the latest entry. Terms are in [`GLOSSARY.md`](../GLOSSARY.md).

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

## Posted entry

A remote ticket's journal lives upstream: `checkpoint` posts every new entry as one comment on the GitHub issue or Azure DevOps work item, after writing its file. A local ticket's entries stay on disk. Only entries go upstream; the plan, the pull request record and artifacts stay local.

````markdown
sdlc-journal-entry `2026-11-23T14-05-09Z.md`

# Journal entry - [...](...)
...
````

- **Marker.** The comment's first line is exactly `` sdlc-journal-entry `{entry file name}` ``, the name the entry has in `journal/`. It matches ``^sdlc-journal-entry `(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z\.md)`$``, and the capture is the file name. A comment whose first line does not match is not a journal entry, whatever else it says. The backticks keep a renderer from linking the name as a `.md` domain.
- **Posted form.** The marker line, one blank line, then the entry file's content verbatim: the full entry, never a summary. Both sources take Markdown; how each is posted is in its provider note (`providers/github.md`, `providers/ado.md`).
- **Posted once, never edited or deleted**, like the file. A correction is a new entry, posted as its own comment.
- **Unposted entries.** An entry whose post fails keeps its file and is listed in `ticket.json` `unposted_journal`: file names, oldest first. The next checkpoint posts that backlog, oldest first, before its own entry, removing each name as its comment lands, and the key when none is left. Before re-posting a listed entry, read the ticket's comments and drop the name if its marker is already there: a post can land even when its answer is lost.
- **Not backfilled.** Entries written before a ticket's journal was posted stay local; the next entry carries forward what is open.

## Mirrored entry

A remote ticket's `journal/` is part of its mirror. `fetch`, run by `intake`, writes each marked comment upstream as the file its marker names, holding the entry as posted: the comment after the marker line and the blank line. A file already in `journal/` is never overwritten, so a mirror only gains entries. Its report's `fetched.journal` lists the names `written` and those `kept`.

- **Read tolerantly.** Whitespace, a BOM and CRLF around the marker line do not hide it. A name posted twice counts once, as first posted.
- **The latest entry** is the greatest name among `journal/` and the entries upstream: names sort in time order on every machine. An unposted entry is in `journal/` only; an entry another machine posted is upstream only until the next intake.
- **`fetch --check`** adds, for a remote ticket it reached upstream:
  - `journal`: `upstream`, every entry's name, oldest first; `unmirrored`, those `journal/` lacks; and while any is unmirrored, `newest_unmirrored`, `{name, entry, author}`, the newest of them in full. With `changed` it reads the live comments, otherwise the mirror's.
  - `only_journal`, with `changed` only: true when nothing but journal entries differs from the mirror. Every post moves the revision, so after a checkpoint `changed` is true and `only_journal` says that is all it was.

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
