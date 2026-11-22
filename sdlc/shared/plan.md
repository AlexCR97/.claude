# Plan

The format of `plan.md`, the file in a ticket directory that holds the phased plan, and the step status vocabulary every skill that reads or writes it uses. Written by `plan`; its statuses are kept honest by `implement` and `checkpoint`. The types that shape its phases are in [`types.md`](./types.md).

## Template

````markdown
# Implementation Plan - [{reference}: {title}]({url or raw/ticket.md})

> Generated on {date} UTC. Source of truth: {the mirror in raw/, or raw/ticket.md}
> Session history: [journal/](journal/)

## Progress

| Phase                          | Activity   | Estimate          | Status      |
| ------------------------------ | ---------- | ----------------- | ----------- |
| [Prerequisites](#prerequisites) | -          | -                 | [ ] Pending |
| [Phase 1: {name}](#{anchor})   | {activity} | ~{hours} hrs      | [ ] Pending |
| **Total**                      |            | **~{total} hrs**  |             |

## Workspace

### Scan roots

- `{absolute directory}` - {default scan root | given by the user | invocation directory | found by search}

### Worktrees

| Repository | Branch | Kind          | Path                   |
| ---------- | ------ | ------------- | ---------------------- |
| {name}     | {name} | main / linked | `{absolute directory}` |

### Plain directories

| Plain directory | Path                   |
| --------------- | ---------------------- |
| {name}          | `{absolute directory}` |

### Projects

| Project | Lives in                          | Path                      | Technology |
| ------- | --------------------------------- | ------------------------- | ---------- |
| {name}  | {repository, repository@branch or plain directory} | {relative to Lives in} | {technology} |

## Prerequisites

- [ ] {something that must be true before any phase starts}

## Phase 1: {name} (~{hours} hrs)

**Scope:** {one sentence}

**Activity:** {one of TDD, Development, Testing, Design, Deployment, Documentation, Human Review}

**Projects touched:** {projects}

### Step 1.1

**Status:** Pending

**Target:** `{path relative to its project's worktree}`

**Artifacts:** -

{what to do and why, specific enough to act on}
````

## Rules

- **The header links the ticket**: its URL for a remote ticket, `raw/ticket.md` for a local one. A plan never restates the ticket's content, only what the work needs from it.
- **The Workspace section lists only what the plan works in** (see `conventions.md`). Its paths are absolute; the Projects table's path is relative to the worktree or plain directory in its `Lives in` column. Omit a table with no rows.
- **Prerequisites** is omitted when empty.
- **A phase** has one Activity and one scope sentence. Estimates are the model's judgement, always written with `~`.
- **A step** names one target: a path relative to its project's worktree, with `in {repository@branch}` added when the workspace holds more than one worktree of that repository. A step with no file target, such as one that answers a question, names what it produces instead.
- **`**Artifacts:**`** holds paths relative to `plan.md` of anything a step produced or rests on, or `-`. Nothing generated is written directly in the ticket directory; it goes under `artifacts/`.
- **Progress rows link to their phase heading**: the heading's GitHub slug (lowercase, drop everything but letters, digits, spaces and hyphens, spaces to hyphens), the estimate included.
- **Order of phases**: type-required phases first (see `types.md`), then prerequisites of the work (design, data, backend, shared libraries, frontend), then tests, documentation and deployment. A Human Review phase sits right after the phase it gates.

## Status

A step's `**Status:**` line holds exactly one value, optionally followed by ` - ` and a one-line note.

| Status        | Means                | Note                                              |
| ------------- | -------------------- | ------------------------------------------------- |
| `Pending`     | Not started          | None                                              |
| `In Progress` | Started, not finished | **Required**: what is done and what remains      |
| `Blocked`     | Cannot proceed       | **Required**: what blocks it and what would clear it |
| `Done`        | Finished             | Optional: only where the outcome differed from the step |

- A new plan uses `Pending` only. Never write a bare `In Progress` or `Blocked`.
- A phase's Progress row is derived, never set: any step `Blocked` gives `[!] Blocked`; every step `Done` gives `[x] Done`; any `Done` or `In Progress` step gives `[~] In Progress`; otherwise `[ ] Pending`. A short parenthetical may follow where the count misleads, as in `[x] Done (4 skipped)`.
- A phase is never `[x] Done` while a step is not `Done`.
- A note says what state a step is in; why it is in that state belongs in the journal.

## Project signals

A project is a directory marked by a build or deployment file. The first match names its technology; add a row only where a file is not listed here.

| File                                                                  | Technology                |
| --------------------------------------------------------------------- | ------------------------- |
| `*.sln`, `*.csproj`                                                   | .NET                      |
| `package.json`                                                        | Node, or a frontend app when it names a framework |
| `pyproject.toml`, `requirements.txt`, `setup.py`                      | Python                    |
| `pom.xml`, `build.gradle*`                                            | JVM                       |
| `go.mod`, `Cargo.toml`                                                | Go, Rust                  |
| `Dockerfile`, `docker-compose.yml`                                    | Containerized service     |
| `*.bicep`, `*.tf`, `azure-pipelines.yml`, `.github/workflows/`        | Infrastructure or CI/CD   |
| `openapi.json`, `swagger.json`, `*.http`                              | API contract              |
