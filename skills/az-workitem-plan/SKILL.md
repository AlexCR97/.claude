---
name: az-workitem-plan
description: Follow-up to az-workitem-digest. Reads the digest.md for a work item, analyzes the current codebase to discover related services and projects, and produces a phased, file-level implementation plan written to plan.md. Researches unknowns that would change the plan, storing scripts and findings under artifacts/planning/ and asking first before running any script. On subsequent runs, shows progress and updates step status. Makes NO code changes.
---

## Scope

This skill is a **planning-only** tool. It reads, analyzes, and writes documentation. It must **never** create, edit, or delete source code files, run migrations, install packages, or make any change to the codebase being analyzed.

"Planning-only" constrains what this skill may change, not what it may learn. Producing research artifacts — a probe script, its captured output, an inventory, a findings note — is part of planning and belongs under `artifacts/planning/` (see [Paths](#paths) and [step 7](#7-research-unknowns-that-would-change-the-plan)). A plan built on an unverified assumption is worth less than the hour spent verifying it.

The `digest.md` is the **single source of truth** for all ADO work item context during planning. Planning reasoning must be derived exclusively from:

- `digest.md`
- the downloaded attachments it references (under `~/.az-workitems/{id}/raw/`)
- any artifacts a previous run left under `~/.az-workitems/{id}/artifacts/`
- the codebase being planned against

**Never read `raw.json`.** If `digest.md` is missing information needed to plan, ask the user or run `/az-workitem-refine {id}` followed by `/az-workitem-digest {id}` — do not fall back to the raw data.

---

## Paths

All `az-workitem-*` data lives under the current user's home directory, so the paths below are the same no matter which workspace the session runs in:

```
~/.az-workitems/
```

`~` is written for brevity. Neither the file tools nor a quoted shell argument expand it, so **resolve it to an absolute path before use** — `C:\Users\{user}` on Windows, `/home/{user}` on Linux, `/Users/{user}` on macOS.

### Work item directory layout

```
~/.az-workitems/{id}/
├── digest.md              ← az-workitem-digest
├── journal.md             ← az-workitem-checkpoint (not this skill's — see below)
├── plan.md                ← az-workitem-plan
├── raw/                   ← az-workitem-fetch (raw.json + attachments)
└── artifacts/             ← files generated while planning or implementing
    ├── planning/          ← research done to build the plan itself
    ├── shared/            ← artifacts spanning more than one step
    └── step-{N}.{M}/      ← everything one plan step produced
```

`artifacts/` and its subdirectories are created lazily — only when a run actually produces a file. The work item root holds nothing but the five entries above: **never write a generated file directly into `~/.az-workitems/{id}/`.**

`journal.md` is the per-session work log, and it is **out of scope for this skill: never read it, never write to it.** It belongs to `az-workitem-checkpoint`, which writes it, and to `az-workitem-resume`, which reads it back at the start of a session and brings what matters into the conversation. What a step's state is, this skill reads from `plan.md`; why it is in that state comes from the session, not from the file.

**Placement rules**

- A file belongs to the step that produced it: `artifacts/step-{N}.{M}/`, where `{N}.{M}` matches the `### Step {N}.{M}` heading in `plan.md` exactly.
- A file produced while researching the plan itself — before the steps it informs exist — goes in `artifacts/planning/`.
- A file that more than one step reads, or that applies to the plan as a whole (a findings document, a data extract several steps consult), goes in `artifacts/shared/`.
- The captured output of running a script is written beside it as `{name}.output.{ext}`, where `{ext}` is the format the output actually is — `.json` for a JSON document, `.csv`, `.tsv`, `.jsonl`, `.md`, `.sql`, `.xml`, and so on. **Default to `.txt`**, and reach for a structured extension only when the whole file parses as that format: console output that mixes a table, a log line and a summary is `.txt`, however much JSON it happens to contain. Naming a capture for what it holds is what lets a later run parse it instead of re-running the script to get the data in a usable shape.
- When a structured capture would be spoiled by diagnostics, keep stdout in the structured file and put stderr beside it as `{name}.stderr.txt`. Where output is plain text anyway, one combined `{name}.output.txt` is simpler and preferred.
- Any of these directories may hold a `README.md` recording what was done and what it found. Write one whenever the artifacts alone would not tell a later reader why they exist.

**Renumbering**

Plans change shape: research reorders phases, one step splits into two, a phase turns out to belong earlier. **Renumber whenever the plan reads better for it.** A step number is also a directory name, though, so renumbering is a rename — and it is finished only when nothing still points at the old number:

1. Rename each affected `artifacts/step-{old}/` to `artifacts/step-{new}/`.
2. Update the `## Phase {N}` and `### Step {N}.{M}` headings in `plan.md`.
3. Update every `**Artifacts:**` line that named a renamed directory.
4. Search `plan.md` and every file under `artifacts/` — `planning/`, `shared/`, and each step's `README.md` included — for the old identifiers (`step-1.1`, `Step 1.1`, `Phase 3`) and update each occurrence.
5. Tell the user what moved and why.

Do all five in one pass. A half-renumbered plan, where an `**Artifacts:**` line points at a directory that no longer exists, is worse than one that was never renumbered at all.

---

## Input

The user must supply a **work item ID**. It may be passed as an argument (e.g. `/az-workitem-plan 12345`) or stated in the message. If no ID is provided, ask for one before proceeding.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Locate the digest

Resolve the following against the user's home directory (see [Paths](#paths)):

- Config path: `~/.az-workitems/config.json`
- Digest path: `~/.az-workitems/{id}/digest.md`
- Plan path: `~/.az-workitems/{id}/plan.md`
- Artifacts directory: `~/.az-workitems/{id}/artifacts/` — may not exist yet; absent on a first run

If `config.json` does not exist, stop and tell the user:

> No config found. Run `/az-workitem-init` first to set up your Azure DevOps connection.

If `digest.md` does not exist, stop and tell the user:

> No digest found for work item #{id}. Run `/az-workitem-digest {id}` first.

### 2. Check for an existing plan

If `plan.md` already exists for this work item, **do not regenerate it**. Instead, jump directly to [Subsequent-run flow](#subsequent-run-flow).

---

## First-run Flow

### 3. Read the digest and survey existing work

Parse `digest.md` and extract:

- **Title** and **work item type** (from the `# Work Item Digest` heading)
- **Description** — the TL;DR of the problem or goal; this is the primary input for planning
- **Acceptance Criteria** — the conditions that must be met; use these to derive concrete, actionable steps
- **Related Work Items** — note any child or related IDs that may map to separate services
- **Attachments** — for each attachment listed, if its description suggests it carries information relevant to planning (a mockup, a log file, a spec document, a diagram), open the downloaded file at `~/.az-workitems/{id}/raw/{filename}` and factor its content into the plan. Rely on the digest's existing description first; only open the file itself when more detail is needed than the digest provides.

Then list `~/.az-workitems/{id}/artifacts/` (see [Paths](#paths)). If it exists, a previous run already investigated something. For `planning/`, for each `step-{N}.{M}/`, and for `shared/`, read the `README.md` if present, otherwise skim the artifacts themselves.

Anything measured or established there is **evidence, and outranks assumption**. Do not plan a step that re-derives a fact an existing artifact already settles — reference the artifact instead. If an artifact contradicts `digest.md`, say so to the user and plan around the measured value, not the stated one.

### 4. Discover services in the codebase

Scan the current working directory for signals that identify projects and services. Do **not** read source file contents at this stage — only file names, paths, and directory structure matter here.

Look for the following indicators, in order of priority:

| Signal                                                                     | What it implies                       |
| -------------------------------------------------------------------------- | ------------------------------------- |
| `*.sln`, `*.csproj`                                                        | .NET backend service or library       |
| `package.json` (with `"scripts"."start"` or framework deps)                | Node/JS/TS service or frontend app    |
| `Dockerfile`, `docker-compose.yml`                                         | Containerized service boundary        |
| `*.bicep`, `*.tf`, `*.tfvars`, `azure-pipelines.yml`, `.github/workflows/` | Infrastructure / DevOps / CI-CD       |
| `**/appsettings*.json`, `**/program.cs`                                    | ASP.NET Web API or background service |
| `angular.json`, `next.config.*`, `vite.config.*`, `nuxt.config.*`          | Frontend SPA framework                |
| `*migrations*`, `*schema*`, `*seed*` (directories or files)                | Database layer                        |
| `*.http`, `openapi.json`, `swagger.json`                                   | API contract definitions              |

Group discovered items into service categories:

- **Backend** — APIs, microservices, background workers, libraries
- **Frontend** — SPAs, MFEs, portals
- **Database** — migration projects, schema definitions
- **DevOps / Infra** — CI pipelines, IaC, Dockerfiles, Helm charts
- **Contracts / Shared / Common** — shared libraries, NuGet/npm packages, OpenAPI specs

### 5. Present discoveries and confirm with the user

Show the user a summary of what was found, grouped by category. For example:

```
I found the following services in the working directory:

Backend
  • src/Api/MyApp.Api.csproj         (.NET 8 Web API)
  • src/Worker/MyApp.Worker.csproj   (.NET 8 background service)

Frontend
  • client/package.json              (React + Vite)

Database
  • src/Migrations/                  (EF Core migrations)

DevOps / Infra
  • .github/workflows/ci.yml
  • infra/main.bicep

Does this look correct? Are there any services I missed or should ignore?
```

Wait for the user's response before continuing.

If the user corrects or adds a path, read only those specific paths/files to gather the missing context, then incorporate the correction. Do not re-scan the entire directory.

If the user confirms with no changes, proceed.

### 6. Analyze relevant services

For each confirmed service that is relevant to the description and acceptance criteria, do a **targeted read** — enough to identify:

- The entry point or main module
- Key directories (controllers, services, components, routes, etc.)
- Existing patterns (naming conventions, folder structure, test locations)
- Files most likely to be touched based on the description and acceptance criteria

The goal is to be able to name specific files and classes in the plan. Read only what is necessary — do not read entire codebases.

### 7. Research unknowns that would change the plan

A plan built on a false assumption is wrong in its *shape*, not just its estimates: phases get sequenced around a bottleneck that is not there, and the effort lands on the wrong candidate. Research is how the plan earns its structure.

Before estimating, name the facts the plan's shape rests on that neither `digest.md` nor the codebase settles — a production row count, whether an index exists, which of two code paths actually runs, the true size of a data set, how long something currently takes. For each, ask: **if this turned out to be wrong by an order of magnitude, would the plan change?** If not, record it as a stated assumption in the plan and move on. If it would, research it now rather than discovering it during implementation.

Reading files needs no permission — the codebase, a local export, an attachment. Writing a script does not need permission either. **Running one always does.**

A script artifact is never executed until the user has approved that specific script. Write it first, then show what it does, what it reads, and where its output will land, and ask:

> To size Phase 2 I need the real number of `UserAuthorization` documents in production — the work item states ~21,000 but nothing has confirmed it. I have written a read-only query at `artifacts/planning/count-authorizations.js`; it runs one `countDocuments` against `analytics-svc-userauthorizations` and writes nothing. May I run it against production?

Wait for the answer, and ask again for each subsequent run — approval covers the run in front of the user, not the script forever. Never write to an external system under any circumstance.

Store everything the research produced under `artifacts/planning/`: the script, its captured output named for the format it holds (see [Paths](#paths)), and a `README.md` recording what was asked, what was measured, and what it settled. Then plan against the measured value, and name the artifact on the `**Artifacts:**` line of every step that rests on it.

If research contradicts `digest.md`, plan around the measured value and tell the user which stated fact it displaced — do not quietly plan against a number the work item still asserts.

### 8. Derive hour estimates

Estimate effort per phase using these heuristics. Estimates are rough guides, not commitments.

| Signal                                              | Baseline |
| --------------------------------------------------- | -------- |
| DB migration (add column / new table)               | 0.5 hr   |
| New API endpoint (controller + service + tests)     | 1.5 hrs  |
| Modify existing API endpoint                        | 0.5–1 hr |
| New frontend component or page                      | 1–2 hrs  |
| Modify existing frontend component                  | 0.5–1 hr |
| Integration / E2E test suite                        | 1-2 hrs  |
| CI pipeline change                                  | 0.5 hr   |
| IaC / infra change                                  | 1 hr     |
| Cross-cutting concern (auth, logging, feature flag) | 1–2 hrs  |

Adjust up for:

- New patterns not already established in the codebase (+50%)
- Changes that touch more than 5 files (+25% per additional 5 files)
- Work item type is Bug with unclear root cause (+1 hr investigation buffer)

Adjust down for:

- Highly repetitive changes following an obvious existing pattern (−25%)

### 9. Assign an Activity Type to each phase

Every phase must declare exactly one **Activity** from the following fixed set:

| Activity      | Use when the phase is primarily...                                             |
| ------------- | -------------------------------------------------------------------------------- |
| Development   | writing or modifying source code (backend, frontend, scripts)                    |
| Testing       | authoring or updating unit, integration, or E2E tests                            |
| Design        | defining schema, API contracts, or architecture before code is written           |
| Deployment    | CI/CD pipeline changes, IaC, release/rollout steps                               |
| Documentation | README, ADRs, comments, or other written artifacts                               |
| Human Review  | a checkpoint requiring manual approval/decision rather than autonomous execution |

If a phase's work spans more than one activity, assign the activity that represents the majority of the effort. If the split is significant, divide the work into separate phases instead.

### 10. Write plan.md

Compose the plan using the template below and write it to:

```
~/.az-workitems/{id}/plan.md
```

Confirm in chat with a **single line** once written:

> Plan written to `~/.az-workitems/{id}/plan.md`

Do not print the plan body in chat.

#### Phase ordering

Order phases by logical dependency — each phase must be completable before the next begins. Within that dependency chain, also order phases by their Activity Type, following the natural execution lifecycle: **Design → Development → Testing → Documentation → Deployment**. A **Human Review** phase is a checkpoint, not a lifecycle stage — place it immediately after the phase(s) whose output it gates, wherever that falls in the sequence.

1. Prerequisites / environment setup
2. Design — schema, API contracts, architecture decisions
3. Database / schema changes
4. Backend — data access layer
5. Backend — business logic / domain
6. Backend — API / contracts
7. Shared libraries or contracts (if updated)
8. Frontend
9. Tests (unit, integration, E2E)
10. Documentation
11. DevOps / CI / deployment

Omit any phase for which there is no work to do.

#### Plan template

Read the template from `skills/az-workitem-plan/plan-template.md` and use it as the structure for the output file.

Rules for the template:

- Every step is its own markdown sub-section under `## Phase {N}`, headed `### Step {N}.{M}` (the phase number, a dot, and the step number within that phase, starting at 1), followed by a `**Status:**` line (see [Step status](#step-status)), a `**Target:**` line naming the file/class, and an `**Artifacts:**` line
- The `**Artifacts:**` line names every file a step **produced or rests on**, as paths relative to `plan.md` — e.g. `**Artifacts:** [artifacts/planning/count-authorizations.output.json](artifacts/planning/count-authorizations.output.json)`. It reads `—` only when a step neither produced anything nor depends on prior research. Planning fills it in with the artifacts from step 7 and with any existing directory for that step; `az-workitem-implement` appends what it produces
- The Progress table sits at the top, immediately after the header, so it is the first thing visible when opening the file; it is updated alongside the phase step statuses on subsequent runs
- Each phase's `**Activity:**` line must use exactly one value from the Activity Type set defined in step 9; the Progress table's Activity column for that phase must match
- The ADO work item URL follows the pattern: `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}` (read `org` and `project` from `~/.az-workitems/config.json`)
- Omit the Prerequisites section if it has no content

#### Step status

A `**Status:**` line takes exactly one of four values, optionally followed by ` — ` and a one-line note:

| Status        | Means                          | Note                                                                    |
| ------------- | ------------------------------ | ----------------------------------------------------------------------- |
| `Pending`     | Not started                    | None                                                                    |
| `In Progress` | Started, not finished          | **Required** — what is done and what remains                            |
| `Blocked`     | Cannot proceed                 | **Required** — what is blocking, and what would clear it                |
| `Done`        | Finished                       | Optional — only where the outcome differed from what the step asked for |

```
**Status:** In Progress — harness runs for the Analytics job; the Identity case throws at startup
**Status:** Blocked — waiting on the Identity team to confirm the claim name
```

`Pending` and `Done` are the only two statuses a freshly generated plan may use — nothing has been started yet, so nothing can be in progress or blocked. The other two are set by `az-workitem-implement`, by `az-workitem-checkpoint`, or on a subsequent run of this skill.

A note is what makes the state actionable in a later session: `In Progress` on its own says a step was touched, which is nearly as unhelpful as `Pending`. Keep it to one line — the fuller account of a session belongs in `journal.md`, which `az-workitem-checkpoint` writes.

The phase's row in the Progress table is **derived** from its steps, never set independently:

| Condition                              | Phase status       |
| -------------------------------------- | ------------------ |
| Any step `Blocked`                     | `[!] Blocked`      |
| Every step `Done`                      | `[x] Done`         |
| Any step `Done` or `In Progress`       | `[~] In Progress`  |
| Otherwise                              | `[ ] Pending`      |

A phase row may carry a short parenthetical where the count alone misleads — `[x] Done (4 skipped)`, `[~] In Progress (2.7 left to run)`.

---

## Subsequent-run Flow

When `plan.md` already exists:

### 3. Read and summarize current progress

Read `plan.md` and list `~/.az-workitems/{id}/artifacts/`. Reconcile the two: if a step has an artifacts directory but its `**Artifacts:**` line still reads `—`, fill the line in. Then recompute each phase's Progress table row from its steps' `**Status:**` lines, using the derivation table in [Step status](#step-status).

Print a compact summary table in chat:

```
Implementation Plan — #{id}: {title}

| Phase                       | Activity    | Estimate     | Status            |
| --------------------------- | ----------- | ------------ | ----------------- |
| Prerequisites               | —           | —            | [x] Done          |
| Phase 1: Database migration | Development | ~0.5 hrs     | [x] Done          |
| Phase 2: Repository layer   | Development | ~1.5 hrs     | [~] In Progress   |
| Phase 3: API endpoint       | Development | ~1.5 hrs     | [!] Blocked       |
| Phase 4: Tests              | Testing     | ~1.5 hrs     | [ ] Pending       |
| **Total**                   |             | **~5 hrs**   | 2 / 5 phases done |
```

Under the table, list every `In Progress` and `Blocked` step with its note, so the reason a phase is not moving is visible without opening the file.

### 4. Ask which phase to update

Ask the user:

> Which phase or step would you like to update? Name a phase or step (e.g. "Step 2.1") and its new status — done, in progress, or blocked — or ask me to research an open question, or say "none" to exit.

Wait for the response.

### 5. Update plan.md

Based on the user's answer:

- If they name a **phase** with no status, or say it is complete: set `**Status:** Done` on every step sub-section within that phase section and update the Progress table row to [x] Done
- If they name a **specific step**: set its `**Status:**` to the status they gave, defaulting to `Done` when they gave none, then recompute the phase's Progress table row from the derivation table in [Step status](#step-status)
- If the new status is `In Progress` or `Blocked`, a note is required. Take it from what the user said; where they gave none, ask for one line rather than writing a bare status:

  > What should Step {N}.{M}'s status note say — {for In Progress: what is done and what remains | for Blocked: what is blocking, and what would clear it}?
- If they ask to **research** something (e.g. "find out whether that index exists"): run [step 7](#7-research-unknowns-that-would-change-the-plan) for that question alone, store what it produces under `artifacts/planning/`, then revise only the steps the finding actually affects — their prose, their estimate, and their `**Artifacts:**` line. Leave every other step's content as it is. If the finding changes the plan's shape, renumber and complete the rename in one pass (see [Paths](#paths)). Report what changed and what it displaced
- Update the Progress table's status column to reflect the new state
- If they say "none" or similar, exit without changes

Confirm with a single line:

> Updated `~/.az-workitems/{id}/plan.md`

---

## Constraints

- **Never create, edit, or delete any source code file** — this skill is planning-only
- **Never run commands** that modify the codebase (no `dotnet`, `npm install`, migrations, git commits, etc.)
- Read only enough of the codebase to produce specific, accurate step descriptions
- Derive all plan content from `digest.md`, the attachments it references, and the codebase — do not fabricate file names or class names that do not exist
- **Never read `raw.json`** — `digest.md` is the single source of truth for the work item's content during planning
- Do not regenerate the plan if `plan.md` already exists unless the user explicitly asks (e.g. "regenerate the plan" or "refresh the plan")
- Hour estimates are heuristic guides only — always qualify them with `~`
- Read `artifacts/` before planning, and never plan work that an existing artifact has already settled
- Never create, edit, or delete a file outside `artifacts/planning/` and `plan.md`. A renumbering pass is the one exception: it renames step directories and fixes references wherever they appear under `artifacts/`
- **Never read or write `journal.md`** — it belongs to `az-workitem-checkpoint` and `az-workitem-resume`
- Never write a bare `In Progress` or `Blocked` status: both require a one-line note (see [Step status](#step-status)), and a phase's Progress row is always derived from its steps rather than set independently
- Write research artifacts to `artifacts/planning/` only — never to `artifacts/step-{N}.{M}/` or `artifacts/shared/`, which belong to implementation
- Never run a script artifact without prior authorization — write it, show it, ask, then run. Never run anything that writes to an external system
- Cite a research artifact on the `**Artifacts:**` line of every step whose estimate or approach depends on it — research nothing cites was not worth doing
- Renumber phases and steps whenever the plan's shape calls for it, and finish the rename in one pass (see [Paths](#paths)) so nothing points at an old number
