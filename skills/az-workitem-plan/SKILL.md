---
name: az-workitem-plan
description: Follow-up to az-workitem-digest. Reads the digest.md for a work item, analyzes the current codebase to discover related services and projects, and produces a phased, file-level implementation plan written to plan.md. On subsequent runs, shows progress and updates checkboxes. Makes NO code changes.
---

## Scope

This skill is a **planning-only** tool. It reads, analyzes, and writes documentation.
It must **never** create, edit, or delete source code files, run migrations, install
packages, or make any change to the codebase being analyzed.

---

## Input

The user must supply a **work item ID**. It may be passed as an argument (e.g.
`/az-workitem-plan 12345`) or stated in the message. If no ID is provided, ask for
one before proceeding.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Locate the digest

Resolve the config and digest paths from the **current working directory of the
session** (same `.claude` resolution logic as `az-workitem-digest`):

- If `.claude/` exists in the CWD, use it; otherwise the plan cannot proceed.
- Config path: `.claude/.az-workitems/config.json`
- Digest path: `.claude/.az-workitems/{id}/digest.md`
- Plan path: `.claude/.az-workitems/{id}/plan.md`

If `config.json` does not exist, stop and tell the user:

> No config found. Run `/az-workitem-init` first to set up your workspace.

If `digest.md` does not exist, stop and tell the user:

> No digest found for work item #{id}. Run `/az-workitem-digest {id}` first.

### 2. Check for an existing plan

If `plan.md` already exists for this work item, **do not regenerate it**. Instead,
jump directly to [Subsequent-run flow](#subsequent-run-flow).

---

## First-run Flow

### 3. Read the digest

Parse `digest.md` and extract:

- **Title** and **work item type** (from the `# Work Item Digest` heading)
- **Description** — the TL;DR of the problem or goal; this is the primary input for planning
- **Acceptance Criteria** — the conditions that must be met; use these to derive concrete, actionable steps
- **Related Work Items** — note any child or related IDs that may map to separate services

### 4. Discover services in the codebase

Scan the current working directory for signals that identify projects and services.
Do **not** read source file contents at this stage — only file names, paths, and
directory structure matter here.

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

If the user corrects or adds a path, read only those specific paths/files to gather
the missing context, then incorporate the correction. Do not re-scan the entire
directory.

If the user confirms with no changes, proceed.

### 6. Analyze relevant services

For each confirmed service that is relevant to the description and acceptance
criteria, do a **targeted read** — enough to identify:

- The entry point or main module
- Key directories (controllers, services, components, routes, etc.)
- Existing patterns (naming conventions, folder structure, test locations)
- Files most likely to be touched based on the description and acceptance criteria

The goal is to be able to name specific files and classes in the plan. Read only
what is necessary — do not read entire codebases.

### 7. Derive hour estimates

Estimate effort per phase using these heuristics. Estimates are rough guides, not
commitments.

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

### 8. Write plan.md

Compose the plan using the template below and write it to:

```
.claude/.az-workitems/{id}/plan.md
```

Confirm in chat with a **single line** once written:

> Plan written to `.claude/.az-workitems/{id}/plan.md`

Do not print the plan body in chat.

#### Phase ordering

Order phases by logical dependency — each phase must be completable before the next
begins:

1. Prerequisites / environment setup
2. Database / schema changes
3. Backend — data access layer
4. Backend — business logic / domain
5. Backend — API / contracts
6. Shared libraries or contracts (if updated)
7. Frontend
8. Tests (unit, integration, E2E)
9. DevOps / CI / deployment

Omit any phase for which there is no work to do.

#### Plan template

Read the template from `skills/az-workitem-plan/plan-template.md` and use it as the structure for the output file.

Rules for the template:

- Every step is a checkbox (`- [ ]`)
- The Progress table sits at the top, immediately after the header, so it is the
  first thing visible when opening the file; it is updated alongside the phase
  checkboxes on subsequent runs
- The ADO work item URL follows the pattern:
  `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`
  (read `org` and `project` from `.claude/.az-workitems/config.json`)
- Omit the Prerequisites section if it has no content

---

## Subsequent-run Flow

When `plan.md` already exists:

### 3. Read and summarize current progress

Read `plan.md` and compute the status of each phase by counting its checked vs.
total checkboxes:

- All boxes checked → [x] Done
- Some boxes checked → [~] In Progress
- No boxes checked → [ ] Pending

Print a compact summary table in chat:

```
Implementation Plan — #{id}: {title}

| Phase                       | Estimate     | Status            |
| --------------------------- | ------------ | ----------------- |
| Prerequisites               | —            | [x] Done          |
| Phase 1: Database migration | ~0.5 hrs     | [x] Done          |
| Phase 2: Repository layer   | ~1.5 hrs     | [~] In Progress   |
| Phase 3: API endpoint       | ~1.5 hrs     | [ ] Pending       |
| **Total**                   | **~3.5 hrs** | 2 / 4 phases done |
```

### 4. Ask which phase to update

Ask the user:

> Which phase would you like to mark as complete? You can also name a specific step
> to tick, or say "none" to exit.

Wait for the response.

### 5. Update checkboxes in plan.md

Based on the user's answer:

- If they name a **phase**: tick all step checkboxes within that phase section and
  update the Progress table row to [x] Done
- If they name a **specific step**: tick only that checkbox; if all steps in the
  phase are now checked, also update the Progress table to [x] Done
- Update the Progress table's status column to reflect the new state
- If they say "none" or similar, exit without changes

Confirm with a single line:

> Updated `.claude/.az-workitems/{id}/plan.md`

---

## Constraints

- **Never create, edit, or delete any source code file** — this skill is
  planning-only
- **Never run commands** that modify the codebase (no `dotnet`, `npm install`,
  migrations, git commits, etc.)
- Read only enough of the codebase to produce specific, accurate step descriptions
- Derive all plan content from the digest and the codebase — do not fabricate
  file names or class names that do not exist
- Do not regenerate the plan if `plan.md` already exists unless the user explicitly
  asks (e.g. "regenerate the plan" or "refresh the plan")
- Hour estimates are heuristic guides only — always qualify them with `~`
