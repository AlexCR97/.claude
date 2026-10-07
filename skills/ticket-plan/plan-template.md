# Implementation Plan — [#{id}: {title}]({ticketUrl})

> Generated on {date} at {time} UTC Based on [digest.md](digest.md)
> Session history: [journal.md](journal.md)

## Progress

| Phase                                  | Activity   | Estimate              | Status      |
| -------------------------------------- | ---------- | --------------------- | ----------- |
| [Prerequisites](#prerequisites)        | —          | —                     | [ ] Pending |
| [Phase 1: {phaseName}](#{phaseAnchor}) | {activity} | ~{phaseHours} hrs     | [ ] Pending |
| [Phase 2: {phaseName}](#{phaseAnchor}) | {activity} | ~{phaseHours} hrs     | [ ] Pending |
| ...                                    |            |                       |             |
| **Total**                              |            | **~{totalHours} hrs** |             |

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

## Prerequisites

Before any phase begins, ensure the following are in place:

- [ ] <!-- a prerequisite, e.g. an environment variable set in every target environment, a feature flag in the flag management system, a package in the internal feed -->

---

## Phase 1: {phaseName} (~{phaseHours} hrs)

**Scope:** <!-- one sentence describing what this phase achieves -->

**Activity:** {activity} <!-- exactly one value from Step 10's Activity set -->

**Projects touched:** {projectsTouched}

### Step 1.1

**Status:** {status} <!-- Pending or Done on a first run; ticket-common/STATUS.md has the vocabulary and the note rules -->

**Target:** `{target}`

**Artifacts:** —

<!-- what to do and why, specific enough to act on -->

### Step 1.2

**Status:** {status}

**Target:** `{target}`

**Artifacts:** —

<!-- what to do and why, specific enough to act on -->

### Step 1.M

...

---

## Phase N: {phaseName} (~{phaseHours} hrs)

...
