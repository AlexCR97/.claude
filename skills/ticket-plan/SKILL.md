---
name: ticket-plan
description: Follow-up to ticket-digest. Reads the digest.md for a ticket, analyzes the current codebase to discover related services and projects, and produces a phased, file-level implementation plan written to plan.md. Researches unknowns that would change the plan, storing scripts and findings under artifacts/planning/, and asking first before running any script. On subsequent runs, shows progress and updates step status. Makes NO code changes.
argument-hint: "<[source:]id> [--type T]"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | **only `links.md`** — this skill is forbidden the raw data, so it needs no field map |
| `ticket-types/{type}.md` | everything specific to what shape the work is | only the **resolved** type's file |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

**No `allowed-tools` on this skill, deliberately.** It would like the guarantee `ticket-resume` has, and cannot have it: [step 7](#7-research-unknowns-that-would-change-the-plan) legitimately writes and runs user-approved probe scripts, whose commands are not knowable in advance. An allowlist here would either be too narrow to permit the work or too broad to mean anything. Do not add one.

> **A third axis is still hardcoded here, knowingly.** The service-discovery signal table in [step 4](#4-discover-services-in-the-codebase) and the estimate heuristics in [step 8](#8-derive-hour-estimates) are *stack*-specific, not source- or type-specific. Generalizing them would deserve its own directory of conventions per language, exactly as the two axes above have. That is out of scope here, and flagged rather than expanded.

---

## Scope

This skill is a **planning-only** tool. It reads, analyzes, and writes documentation. It must **never** create, edit, or delete source code files, run migrations, install packages, or make any change to the codebase being analyzed.

"Planning-only" constrains what this skill may change, not what it may learn. Producing research artifacts — a probe script, its captured output, an inventory, a findings note — is part of planning and belongs under `artifacts/planning/` (see `ticket-common/ARTIFACTS.md` and [step 7](#7-research-unknowns-that-would-change-the-plan)). A plan built on an unverified assumption is worth less than the hour spent verifying it.

`digest.md` is the **single source of truth** for the ticket's content during planning. Planning reasoning must be derived exclusively from:

- `digest.md`
- the downloaded attachments it references, under the ticket's `raw/` directory
- any artifacts a previous run left under the ticket's `artifacts/`
- the codebase being planned against
- `ticket-types/{type}.md`, for the shape the plan must take

**Never read the source's raw data** — `digest.md` is the single source of truth for the ticket's content during planning. If `digest.md` is missing information needed to plan, ask the user or run `/ticket-refine {ref}` followed by `/ticket-digest {ref}` — do not fall back to the raw snapshot.

`journal.md` is the per-session work log, and it is **out of scope for this skill: never read it, never write to it.** It belongs to `ticket-checkpoint`, which writes it, and to `ticket-resume`, which reads it back at the start of a session and brings what matters into the conversation. What a step's state is, this skill reads from `plan.md`; why it is in that state comes from the session, not from the file.

---

## Input

```
/ticket-plan <[source:]id> [--type {type}]
```

- `{ref}` — the ticket, optionally prefixed with its source. If none is given, ask for one before proceeding.
- `--type` — override the resolved type. Recorded in `ticket.json`, so a following skill inherits it with no flag.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Resolve the ticket

```bash
python "{skills}/ticket-common/ticket.py" resolve "{ref}" --require digest [--type {type}]
```

Everything below uses the paths, type and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `digest` requirement means there is nothing to plan from; the hint names the skill that fixes it.

The resolver's `artifacts_dir` may not exist yet — it is absent on a first run.

### 2. Read the type contract, then check for an existing plan

Read **`ticket-types/{type}.md`**, specifically its *"What shape the plan takes"* and *"What done means"* sections. They supply this plan's required phases, its forbidden phases, the kind of thing a step delivers, the activity mix, and any estimate adjustment. Everything in the first-run flow below is shaped by them.

If `plan.md` already exists for this ticket, **do not regenerate it**. Jump directly to [Subsequent-run flow](#subsequent-run-flow).

---

## First-run Flow

### 3. Read the digest and survey existing work

Parse `digest.md` and extract:

- **Title** and **type** (from the heading and the Metadata table)
- **Description** — the TL;DR of the problem or goal; this is the primary input for planning
- **Acceptance Criteria** — the conditions that must be met; use these to derive concrete, actionable steps
- **Related Tickets** — note any child or related ids that may map to separate services
- **Attachments** — for each attachment listed, if its description suggests it carries information relevant to planning (a mockup, a log file, a spec document, a diagram), open the downloaded file under the ticket's `raw/` and factor its content into the plan. Rely on the digest's existing description first; only open the file itself when more detail is needed than the digest provides.

Then list the ticket's `artifacts/`. If it exists, a previous run already investigated something. For `planning/`, for each `step-{N}.{M}/`, and for `shared/`, read the `README.md` if present, otherwise skim the artifacts themselves.

Anything measured or established there is **evidence, and outranks assumption**. Do not plan a step that re-derives a fact an existing artifact already settles — reference the artifact instead. If an artifact contradicts `digest.md`, say so to the user and plan around the measured value, not the stated one.

### 4. Discover services in the codebase

Scan the current working directory for signals that identify projects and services. Do **not** read source file contents at this stage — only file names, paths, and directory structure matter here.

Look for the following indicators, in order of priority:

| Signal | What it implies |
| --- | --- |
| `*.sln`, `*.csproj` | .NET backend service or library |
| `package.json` (with `"scripts"."start"` or framework deps) | Node/JS/TS service or frontend app |
| `Dockerfile`, `docker-compose.yml` | Containerized service boundary |
| `*.bicep`, `*.tf`, `*.tfvars`, `azure-pipelines.yml`, `.github/workflows/` | Infrastructure / DevOps / CI-CD |
| `**/appsettings*.json`, `**/program.cs` | ASP.NET Web API or background service |
| `angular.json`, `next.config.*`, `vite.config.*`, `nuxt.config.*` | Frontend SPA framework |
| `*migrations*`, `*schema*`, `*seed*` (directories or files) | Database layer |
| `*.http`, `openapi.json`, `swagger.json` | API contract definitions |

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

> To size Phase 2 I need the real number of `UserAuthorization` documents in production — the ticket states ~21,000 but nothing has confirmed it. I have written a read-only query at `artifacts/planning/count-authorizations.js`; it runs one `countDocuments` against `analytics-svc-userauthorizations` and writes nothing. May I run it against production?

Wait for the answer, and ask again for each subsequent run — approval covers the run in front of the user, not the script forever. Never write to an external system under any circumstance.

Store everything the research produced under `artifacts/planning/`, following `ticket-common/ARTIFACTS.md`: the script, its captured output named for the format it holds, and a `README.md` recording what was asked, what was measured, and what it settled. Then plan against the measured value, and name the artifact on the `**Artifacts:**` line of every step that rests on it.

If research contradicts `digest.md`, plan around the measured value and tell the user which stated fact it displaced — do not quietly plan against a number the ticket still asserts.

### 8. Derive hour estimates

Estimate effort per phase using these heuristics. Estimates are rough guides, not commitments.

| Signal | Baseline |
| --- | --- |
| DB migration (add column / new table) | 0.5 hr |
| New API endpoint (controller + service + tests) | 1.5 hrs |
| Modify existing API endpoint | 0.5–1 hr |
| New frontend component or page | 1–2 hrs |
| Modify existing frontend component | 0.5–1 hr |
| Integration / E2E test suite | 1–2 hrs |
| CI pipeline change | 0.5 hr |
| IaC / infra change | 1 hr |
| Cross-cutting concern (auth, logging, feature flag) | 1–2 hrs |

Adjust up for:

- New patterns not already established in the codebase (+50%)
- Changes that touch more than 5 files (+25% per additional 5 files)

Adjust down for:

- Highly repetitive changes following an obvious existing pattern (−25%)

**Then apply whatever estimate adjustment `ticket-types/{type}.md` names**, and any cap it imposes. A type's adjustment is on top of these, not instead of them.

### 9. Assign an Activity Type to each phase

Every phase must declare exactly one **Activity** from the following fixed set:

| Activity | Use when the phase is primarily... |
| --- | --- |
| Development | writing or modifying source code (backend, frontend, scripts) |
| Testing | authoring or updating unit, integration, or E2E tests |
| Design | defining schema, API contracts, or architecture before code is written |
| Deployment | CI/CD pipeline changes, IaC, release/rollout steps |
| Documentation | README, ADRs, comments, or other written artifacts |
| Human Review | a checkpoint requiring manual approval/decision rather than autonomous execution |

This set is **this plan's own taxonomy** — nothing is ever written back to any ticket source with these values, so no source may extend or rename them. A type file **selects from** this set, and may forbid a value; it never adds one.

If a phase's work spans more than one activity, assign the activity that represents the majority of the effort. If the split is significant, divide the work into separate phases instead.

### 10. Write plan.md

Compose the plan using the template and write it to the resolved `plan` path.

Confirm in chat with a **single line** once written:

> Plan written to `{plan path}`

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

**Where the type file requires a phase, it comes first regardless of this ordering** — a characterization or a reproduction phase exists precisely to run before anything else. **Where the type file forbids a phase or an Activity value, that prohibition wins over this list.** And where the type file says a plan of this kind is normally a single phase, do not invent phases to fill the template.

#### Plan template

Read the template from `{skills}/ticket-plan/plan-template.md` and use it as the structure for the output file.

Rules for the template:

- Every step is its own markdown sub-section under `## Phase {N}`, headed `### Step {N}.{M}` (the phase number, a dot, and the step number within that phase, starting at 1), followed by a `**Status:**` line, a `**Target:**` line naming the file/class or the artifact the step delivers, and an `**Artifacts:**` line
- The `**Artifacts:**` line follows `ticket-common/ARTIFACTS.md`. Planning fills it in with the artifacts from step 7 and with any existing directory for that step; `ticket-implement` appends what it produces
- The Progress table sits at the top, immediately after the header, so it is the first thing visible when opening the file; it is updated alongside the phase step statuses on subsequent runs
- Every row's Phase cell links to that phase's own section — `[Phase 1: Database migration](#phase-1-database-migration-05-hrs)`, and `[Prerequisites](#prerequisites)` for the prerequisites row. The anchor is the GitHub slug of the full `##` heading, estimate included: lowercase it, drop every character that is not a letter, digit, space or hyphen, then turn spaces into hyphens — `## Phase 1: Database migration (~0.5 hrs)` → `#phase-1-database-migration-05-hrs`. A phase renamed, renumbered, or re-estimated has its heading and its link changed together; drop the Prerequisites link where that section is omitted
- Each phase's `**Activity:**` line must use exactly one value from the Activity Type set defined in step 9; the Progress table's Activity column for that phase must match
- `{ticket-url}` is `ticket.json`'s `url`. **Where it is `null`, write the title as plain text rather than a broken link.** For any other reference, use the patterns in `ticket-providers/{source}/links.md`
- Omit the Prerequisites section if it has no content

#### Step status

The four-value vocabulary, the note rules, and the table deriving a phase's Progress row from its steps are in **`ticket-common/STATUS.md`**. Read it rather than restating it.

`Pending` and `Done` are the only two statuses a freshly generated plan may use — nothing has been started yet, so nothing can be in progress or blocked.

---

## Subsequent-run Flow

When `plan.md` already exists:

### 3. Read and summarize current progress

Read `plan.md` and list the ticket's `artifacts/`. Reconcile the two: if a step has an artifacts directory but its `**Artifacts:**` line still reads `—`, fill the line in. Then recompute each phase's Progress table row from its steps' `**Status:**` lines, using the derivation table in `ticket-common/STATUS.md`, and repair any Phase cell whose link is missing or no longer matches its heading.

Print a compact summary table in chat:

```
Implementation Plan — {ref}: {title}

| Phase                       | Activity    | Estimate   | Status            |
| --------------------------- | ----------- | ---------- | ----------------- |
| Prerequisites               | —           | —          | [x] Done          |
| Phase 1: Database migration | Development | ~0.5 hrs   | [x] Done          |
| Phase 2: Repository layer   | Development | ~1.5 hrs   | [~] In Progress   |
| Phase 3: API endpoint       | Development | ~1.5 hrs   | [!] Blocked       |
| Phase 4: Tests              | Testing     | ~1.5 hrs   | [ ] Pending       |
| **Total**                   |             | **~5 hrs** | 2 / 5 phases done |
```

Under the table, list every `In Progress` and `Blocked` step with its note, so the reason a phase is not moving is visible without opening the file.

### 4. Ask which phase to update

Ask the user:

> Which phase or step would you like to update? Name a phase or step (e.g. "Step 2.1") and its new status — done, in progress, or blocked — or ask me to research an open question, or say "none" to exit.

Wait for the response.

### 5. Update plan.md

Based on the user's answer:

- If they name a **phase** with no status, or say it is complete: set `**Status:** Done` on every step sub-section within that phase section and update the Progress table row to `[x] Done`
- If they name a **specific step**: set its `**Status:**` to the status they gave, defaulting to `Done` when they gave none, then recompute the phase's Progress table row from the derivation table in `ticket-common/STATUS.md`
- If the new status is `In Progress` or `Blocked`, a note is required. Take it from what the user said; where they gave none, ask for one line rather than writing a bare status:

  > What should Step {N}.{M}'s status note say — {for In Progress: what is done and what remains | for Blocked: what is blocking, and what would clear it}?
- If they ask to **research** something (e.g. "find out whether that index exists"): run [step 7](#7-research-unknowns-that-would-change-the-plan) for that question alone, store what it produces under `artifacts/planning/`, then revise only the steps the finding actually affects — their prose, their estimate, and their `**Artifacts:**` line. Leave every other step's content as it is. If the finding changes the plan's shape, renumber and complete the rename in one pass (see `ticket-common/ARTIFACTS.md`). Report what changed and what it displaced
- Update the Progress table to reflect the new state — the status column, plus the Phase cell's link wherever a heading was renamed, renumbered, or re-estimated
- If they say "none" or similar, exit without changes

Confirm with a single line:

> Updated `{plan path}`

---

## Constraints

- **Never create, edit, or delete any source code file** — this skill is planning-only
- **Never run commands** that modify the codebase (no `dotnet`, `npm install`, migrations, git commits, etc.)
- Read only enough of the codebase to produce specific, accurate step descriptions
- Derive all plan content from `digest.md`, the attachments it references, the codebase, and the type file — do not fabricate file names or class names that do not exist
- **Never read the source's raw data** — `digest.md` is the single source of truth for the ticket's content during planning
- Do not regenerate the plan if `plan.md` already exists unless the user explicitly asks (e.g. "regenerate the plan" or "refresh the plan")
- Hour estimates are heuristic guides only — always qualify them with `~`
- Read `artifacts/` before planning, and never plan work that an existing artifact has already settled
- Never create, edit, or delete a file outside `artifacts/planning/` and `plan.md`. A renumbering pass is the one exception: it renames step directories and fixes references wherever they appear under `artifacts/`
- **Never read or write `journal.md`** — it belongs to `ticket-checkpoint` and `ticket-resume`
- Never write a bare `In Progress` or `Blocked` status: both require a one-line note, and a phase's Progress row is always derived from its steps
- Write research artifacts to `artifacts/planning/` only — never to `artifacts/step-{N}.{M}/` or `artifacts/shared/`, which belong to implementation
- Never run a script artifact without prior authorization — write it, show it, ask, then run. Never run anything that writes to an external system
- Cite a research artifact on the `**Artifacts:**` line of every step whose estimate or approach depends on it — research nothing cites was not worth doing
- Renumber phases and steps whenever the plan's shape calls for it, and finish the rename in one pass so nothing points at an old number
- Never violate a phase requirement, a phase prohibition, or an Activity prohibition the resolved type's file states
