# Sync

How a skill keeps a ticket's mirror and its pull request record current itself, so neither waits for `/sdlc:intake` or `/sdlc:checkpoint`. `resume`, `plan`, `implement`, `checkpoint`, `pr` and `deploy` sync at their start, `commit` after it pushes, and `submit` when its revision check finds the mirror behind an edit. Terms are in [`GLOSSARY.md`](../GLOSSARY.md); the record's format is [`journal.md`](journal.md) "Pull request record".

## The verb

`python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" sync <reference> [--pull <url> ...]`, adding `--context {namespace}[/{product}]` when the session has one. It writes only the local mirror and `pulls.md`, so it asks nothing, under the ship flag or not.

1. `fetch --check`; when anything besides this machine's own journal posts changed (any `status` but `unchanged`, `journal_only` and `local`), the mirror is refreshed as `fetch` refreshes it, journal entries included.
2. The pull requests whose head is a branch in the Worktrees table of the plan's Workspace, on GitHub or Azure Repos by the worktree's `origin`; a protected branch, a directory not on this machine and another host are skipped. Every pull request already in `pulls.md`, and each `--pull` URL, joins them: `--pull` is how a pull request opened or named in the session is added.
3. Every status is read anew, together, and `pulls.md` is rewritten under one time, lines in their old order with new ones after.

It prints:

```json
{
  "ref": "github:1234",
  "ticket_dir": "...",
  "changed": true,
  "upstream": {
    "status": "changed",
    "refreshed": true,
    "fields": ["description", "acceptance_criteria"],
    "journal": ["2026-11-25T10-00-00Z.md"]
  },
  "pulls": {
    "changed": true,
    "lines": [{ "label": "acme/billing-app#12", "url": "https://github.com/acme/billing-app/pull/12", "status": "open, checks passing" }],
    "skipped": [{ "path": "...", "branch": "main", "reason": "a protected branch heads no pull request of a ticket" }]
  }
}
```

- **`changed`** is true when the mirror was refreshed or a line of `pulls.md` differs from before.
- **`upstream.status`** is `fetch --check`'s ([`journal.md`](journal.md) "Mirrored entry"); `local` for a local ticket.
- **`upstream.fields`** names what the refresh changed, in the ticket's terms: `title`, `state`, `description`, `acceptance_criteria`, `comments` (journal entries left out), and `labels`, `parent`, `sub_issues`, `blocked_by`, `blocking` on GitHub, `tags`, `relations` and any other field by its reference name (`System.AssignedTo`) on Azure DevOps. GitHub's criteria are the body's `Acceptance Criteria` section; a bug's reproduction steps count as its description. Empty for a mirror refreshed from none.
- **`upstream.journal`** names the entries the refresh mirrored: posted from another machine or by another person.

## Reporting

- **Nothing changed** (`changed` false): say nothing.
- **Something changed**: one line naming the fields, the journal entries and the pull requests whose status moved. It stops nothing, with one exception:
- **`description` or `acceptance_criteria` changed under an existing `plan.md`**: the plan may no longer fit the ticket. Name the fields and ask whether to revise the plan through `/sdlc:plan` or carry on. Under the ship flag, carry on: state it as an `(assumed)` decision (the fields that changed, and that the run kept the plan), so `checkpoint` records it, and `pr` names the change in a Pre-merge line of the pull request body.
- **A failure** (signed out, offline, refused) exits non-zero with its error. Report the error in one line and carry on: a failed sync never blocks the skill. The mirror and `pulls.md` stay as they were, and an existing `pulls.md` gains `Refresh failed: {reason}.`, which the next successful sync drops.
