# Implementation Plan — [#{id}: {title}]({ticket-url})

> Generated on {YYYY-MM-DD} at {HH:MM} UTC Based on [digest.md](digest.md)
> Session history: [journal.md](journal.md)

## Progress

| Phase                                  | Activity   | Estimate     | Status      |
| -------------------------------------- | ---------- | ------------ | ----------- |
| [Prerequisites](#prerequisites)        | —          | —            | [ ] Pending |
| [Phase 1: {name}](#phase-1-name-x-hrs) | {Activity} | ~{X} hrs     | [ ] Pending |
| [Phase 2: {name}](#phase-2-name-x-hrs) | {Activity} | ~{X} hrs     | [ ] Pending |
| ...                                    |            |              |             |
| **Total**                              |            | **~{X} hrs** |             |

---

## Workspace

### Scan roots

- `{absolute path}` — {default scan root | given by the user | invocation directory | found by search}

### Worktrees

| Repository | Branch   | Kind             | Path              |
| ---------- | -------- | ---------------- | ----------------- |
| {name}     | {branch} | {main \| linked} | `{absolute path}` |

### Plain directories

| Plain directory | Path              |
| --------------- | ----------------- |
| {name}          | `{absolute path}` |

### Projects

| Project | Lives in                                             | Path                              | Technology |
| ------- | ---------------------------------------------------- | --------------------------------- | ---------- |
| {name}  | {repository \| repository@branch \| plain directory} | {path relative to where it lives} | {stack}    |

## Prerequisites

Before any phase begins, ensure the following are in place:

- [ ] {prerequisite — e.g. environment variable X is set in all target environments}
- [ ] {prerequisite — e.g. feature flag Y exists in the flag management system}
- [ ] {prerequisite — e.g. NuGet package Z is available in the internal feed}

---

## Phase 1: {name} (~{X} hrs)

**Scope:** {one sentence describing what this phase achieves}

**Activity:** {Development | Testing | Design | Deployment | Documentation | Human Review}

**Projects touched:** {comma-separated list}

### Step 1.1

**Status:** Pending | In Progress — {what is done, what remains} | Blocked — {what is blocking, what would clear it} | Done

**Target:** `{File/Class}`

**Artifacts:** —

{what to do and why, specific enough to act on}

### Step 1.2

**Status:** Pending

**Target:** `{File/Class}`

**Artifacts:** —

{what to do and why, specific enough to act on}

### Step 1.M

...

---

## Phase N: {name} (~{X} hrs)

...
