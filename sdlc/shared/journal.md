# Journal

The format of a ticket's journal (`journal/`), of a journal entry posted upstream, and of the pull request record (`pulls.md`). Entries are written and posted only by `checkpoint`, mirrored from upstream by `fetch`; `resume` reads the latest entry. `sync` rewrites the pull request record ([`sync.md`](sync.md)). Terms are in [`GLOSSARY.md`](../GLOSSARY.md).

## Entry file

- **Name:** `journal/{YYYY-MM-DD}T{HH-MM-SS}Z.md`, the UTC time the entry is written, with `-` where a clock has `:`. The names sort in time order. Read the clock in UTC (`date -u +%Y-%m-%dT%H-%M-%SZ`, or `(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ssZ")`).
- **Created once, never edited or deleted.** Before writing, list `journal/` and confirm the name is free; when it is taken, use the next free second. A correction is a new entry that says what it corrects.
- **The latest entry stands alone.** It carries forward every question and blocker still open from the previous one. An item is dropped only when this session resolved it, and the entry says how under Decisions.
- **No ticket location inside an entry.** The directory is the record of where a ticket is filed, and a stored location goes stale. A reference to another ticket is short within this ticket's product and qualified across products.

## Entry

An entry is about 250 words: what a later session needs to pick the work up, and nothing it can read for itself from git, the plan or the ticket. Each line is one fact, written once.

````markdown
# Journal entry - [{reference}: {title}]({url or raw/ticket.md})

## {YYYY-MM-DD HH:MM} UTC - {stage}

**Where:** `{repository}` @ `{branch}`, HEAD `{sha}` ({subject}){, base `{base branch}`}

**Worktree state:** {N modified, N untracked, uncommitted}

**Stopped at:** {the step and its honest state, in at most two sentences}

**Next:** {the single next action, in one sentence}

**Ship run:** {end point}

### Done

- {one outcome, in one line}

### Decisions

- **{what was decided}** - {why, over what}{; cost if wrong: {what breaks or must be redone}}
- **{what was assumed}** (assumed) - {its basis}{; cost if wrong: ...}

### Open questions

- {the question, and who or what can answer it}

### Blockers

- {the blocker, and what would clear it}
````

- **Stage** is `Phase N, Step N.M`, or `Planning`, `Refinement` or `Review`.
- **Where, Stopped at and Next are always present.** Where names the repository by name and the base only when it is not the default branch. Outside a repository, `**Where:** not in a repository`. When the work spans several worktrees, write one Where, and one Worktree state when it applies, per worktree.
- **Worktree state is present only when the worktree is not clean**: uncommitted or untracked files.
- **Next is specific enough to start on without re-reading anything**: a file and an action, never a bare "Continue Phase 2". When nothing is pending: `Nothing pending; all phases complete. Awaiting review.`
- **The Ship run line is in an entry a ship run wrote, and only there**, naming the run's end point: `checkpoint` writes it under the ship flag. `pr` lists the decisions of every entry so marked, whichever run wrote it, so a resumed run keeps the first run's.
- **Done holds at most five outcomes**, each one line: what changed, never an attempt or what the session merely observed.
- **A decision is one line**: what was decided in bold, then why. Under the ship flag it ends with its cost if wrong, as [Ship runs](conventions.md#ship-runs) says; elsewhere the cost is optional. What the plan left unspecified and the session assumed is a decision marked `(assumed)`, its basis as the why. A decision copied from the plan's Decisions (`plan.md`) keeps its wording, less its `Affects` clause.
- **Decisions stated earlier in the session**, such as an `implement` run's report, are carried over: that report is their only record. Every decision reaches the entry, so an entry with many runs past the budget there and nowhere else.
- **Open questions and Blockers are one line each.**
- **Omit an empty Done, Decisions, Open questions or Blockers section.**
- **This shape is for new entries.** An earlier entry, and the comment that posted it, keep the shape they were written in; a reader takes its Inferences section as assumed decisions.

An entry in this shape:

````markdown
# Journal entry - [#1234: Cache the ledger lookup](https://github.com/acme/ledger/issues/1234)

## 2026-11-25 17:15 UTC - Phase 2, Step 2.1

**Where:** `ledger` @ `feat/1234-cache-ledger`, HEAD `8b6f2655` (feat(ledger): cache account lookups)

**Worktree state:** 2 modified, 1 untracked, uncommitted

**Stopped at:** Step 2.1's eviction test is written and fails as expected; the eviction itself is half-done in `LedgerCache.cs`.

**Next:** Make `LedgerCacheTests.Evicts_after_ttl` pass by evicting expired entries in `LedgerCache.Get`.

**Ship run:** pr

### Done

- Phase 1 committed: the cache interface and its in-memory implementation.
- Wrote the failing eviction test for Step 2.1.

### Decisions

- **Cache per account, not per query** - every query reads one account, and per-query keys would duplicate entries; cost if wrong: the cache keys and their tests are redone.
- **A five-minute TTL** (assumed) - the ticket names no lifetime, and balances settle within minutes; cost if wrong: one constant changes.

### Open questions

- Should a balance change evict at once? The product owner can answer.
````

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

A remote ticket's `journal/` is part of its mirror. `fetch`, run by `intake` and `sync`, writes each marked comment upstream as the file its marker names, holding the entry as posted: the comment after the marker line and the blank line. A file already in `journal/` is never overwritten, so a mirror only gains entries. Its report's `fetched.journal` lists the names `written` and those `kept`.

- **Read tolerantly.** Whitespace, a BOM and CRLF around the marker line do not hide it. A name posted twice counts once, as first posted.
- **The latest entry** is the greatest name among `journal/` and the entries upstream: names sort in time order on every machine. An unposted entry is in `journal/` only; an entry another machine posted is upstream only until the next intake.
- **`fetch --check`** adds, for a remote ticket it reached upstream:
  - `journal`: `upstream`, every entry's name, oldest first; `unmirrored`, those `journal/` lacks; and while any is unmirrored, `newest_unmirrored`, `{name, entry, author}`, the newest of them in full. With `changed` it reads the live comments, otherwise the mirror's.
  - `status`, the one value a skill acts on. Every post moves the revision, so after a checkpoint `changed` is true and `status` says whether that is all it was:
    - `unchanged`: the revision has not moved, and `journal/` holds every entry upstream.
    - `journal_only`: nothing but journal entries differs from the mirror, all of them already in `journal/` (this machine's own posts).
    - `journal_unmirrored`: nothing but journal entries differs from the mirror, and `journal.unmirrored` lists some `journal/` lacks.
    - `changed`: something besides journal entries differs.
    - `never_mirrored`, `stale_mirror` and `local` are answered before upstream is asked, as the provider notes say.

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
