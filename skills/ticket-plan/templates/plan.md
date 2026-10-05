# Implementation Plan — [#{id}: {title}]({ticketUrl})

> Generated on {date} at {time} UTC Based on [digest.md](../digest.md)
> Session history: [journal.md](../journal.md)

<!-- plan-sync:start — generated from the phase files by `ticket.py plan-sync`; never edit by hand -->
<!-- plan-sync:end -->

---

## Workspace

### Scan roots

<!-- One line per scan root. Its origin is one of: default scan root, given by the user, invocation directory, found by search. -->

- `{scanRootPath}` — {scanRootOrigin}

### Worktrees

<!-- One row per worktree in the workspace. Kind is main or linked. -->

| Repository   | Branch   | Kind           | Path             |
| ------------ | -------- | -------------- | ---------------- |
| {repository} | {branch} | {worktreeKind} | `{worktreePath}` |

### Plain directories

| Plain directory | Path              |
| --------------- | ----------------- |
| {directoryName} | `{directoryPath}` |

### Projects

<!-- One row per project. Lives in is its repository, repository@branch where the workspace holds more than one worktree of it, or its plain directory; the path is relative to there. -->

| Project       | Lives in  | Path          | Technology   |
| ------------- | --------- | ------------- | ------------ |
| {projectName} | {livesIn} | {projectPath} | {technology} |
