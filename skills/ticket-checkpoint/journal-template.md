# Journal entry — [#{id}: {title}]({ticketUrl})

> Written only by `/ticket-checkpoint`, and read only by `/ticket-resume`. This file is one session's account of itself; it is never edited. Record a correction as a new entry that says what it corrects.

## {timestamp} UTC — {stage}

<!-- stage: "Phase N, Step N.M", or Planning, Refinement or Review -->

**Where:** `{repository}` @ `{branch}` in `{worktree}` — HEAD `{headSha}` ({headSubject}), base `{baseBranch}` @ `{baseSha}`

**Worktree state:** {worktreeState} <!-- clean, or "N modified, N untracked — uncommitted"; append ", N stash(es)" when there are any -->

**Stopped at:** <!-- the step, and the honest state of it — what works, what does not -->

**Next:** <!-- the single next action, specific enough to start on without re-reading anything -->

### Done

- <!-- what actually changed, in terms of files and behavior — not what was attempted -->

### Decisions

- **<!-- the decision -->** — <!-- why, including what it was chosen over -->. Affects {stepId}.

### Inferences

- **<!-- what the plan left unspecified -->** — <!-- what was assumed, and on what basis -->. Affects {stepId}.

### Open questions

- <!-- every question still open, including ones carried forward from the previous entry, and who or what can answer it -->

### Blockers

- <!-- every blocker still open, including ones carried forward from the previous entry, and what would unblock it -->
