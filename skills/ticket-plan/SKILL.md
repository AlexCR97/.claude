---
name: ticket-plan
description: Turns a ticket's digest.md into a phased, file-level implementation plan in plan.md, discovering the repositories, worktrees and projects the work spans from its scan roots. Researches unknowns under artifacts/planning/, asking before running any script. Re-run, it updates step status.
argument-hint: "<ref> [dir ...] [--type type]"
---

Turns a ticket's `digest.md` into a phased, file-level implementation plan in `plan.md`. It discovers the workspace — the repositories, worktrees and projects the work spans — from the ticket's scan roots, researches the facts the plan's shape rests on, and shapes the phases by the ticket's type. Run again on a ticket that has a plan, it shows progress and updates step status. It plans only: research artifacts under `artifacts/planning/` are part of planning — a plan built on an unverified assumption is worth less than the hour spent verifying it — but no change to the workspace is. The terms for code mean what `ticket-common/GLOSSARY.md` says; read it before discovering anything.

End state: `plan.md` written from `digest.md` and the confirmed workspace, every research artifact under `artifacts/planning/` cited by the steps that rest on it, and the workspace unchanged — or, on a later run, `plan.md` updated as the user asked.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                                   |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | **only `links.md`** — this skill is forbidden the raw data, so it needs no field map |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | only the **resolved** type's file                                                    |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

No `allowed-tools`: Step 8 runs user-approved probe scripts whose commands cannot be known in advance.

---

## Parameters

- **`<ref>`** — the ticket, as `ticket-common/RESOLUTION.md` → *How a reference resolves* defines it. Ask for one when it is absent.
- **`[dir ...]`** — one or more directories holding the code for this ticket: a repository's worktree, or a directory holding several repositories. Directories named in the conversation count the same. Each is a scan root and a fact, combined with the default scan roots in Step 4.
- **`[--type type]`** — overrides the resolved type. Recorded in `ticket.json`, so a following skill inherits it with no flag.

---

## Ground rules

1. **Plan only.** Never create, edit or delete a source code file, and never run a command that changes the workspace — no `dotnet`, `npm install`, migrations or commits.
2. **Run read-only git only.** Discovery uses `rev-parse`, `worktree list`, `remote get-url` and `branch --show-current` — never `fetch`, `checkout`, or `worktree add`, `remove` or `prune`.
3. **Plan from `digest.md`, never from the raw data.** Derive content from `digest.md`, the attachments it references, `artifacts/`, the confirmed workspace and the type file; never fabricate a file or class name. Where `digest.md` lacks what the plan needs, ask, or point at `/ticket-refine` then `/ticket-digest`.
4. **Never read or write `journal.md`.** It belongs to `ticket-checkpoint` and `ticket-resume`.
5. **Use the glossary's terms exactly**, in `plan.md` and in chat — never a synonym it retires.
6. **Write only `plan.md` and `artifacts/planning/`.** A renumbering pass is the one exception: it renames step directories and fixes references under `artifacts/`. `artifacts/step-{N}.{M}/` and `artifacts/shared/` belong to implementation.
7. **Never run a script without approval of that run.** Write it, show it, ask, then run; never run anything that writes to an external system.
8. **Never break the type's rules.** A phase requirement, phase prohibition or Activity prohibition in the resolved type's file wins over this file.
9. **Never write a bare `In Progress` or `Blocked` status.** Each needs a one-line note, and a phase's Progress row is always derived from its steps.

---

## Execution Steps

### Step 1 — Resolve the ticket

With a session context, pass `--context {context}` on every `ticket.py` call below that takes one and open the first output line with `Ticket context: {context}` — `ticket-common/RESOLUTION.md` → *The session context* covers overrides.

```bash
python "{skills}/ticket-common/ticket.py" resolve "<ref>" --require digest [--type type] [--context {context}]
```

Everything below uses the paths, type, `product` and `ticket.json` it returns; **every path it prints is absolute**, so nothing here needs expanding. On a non-zero exit, report the message and its hint verbatim and stop. `ticket-common/RESOLUTION.md` carries the full contract — open it only when the output is disputed.

An unmet `digest` requirement means there is nothing to plan from; the hint names the skill that fixes it.

The resolver's `artifacts_dir` may not exist yet — it is absent on a first run.

### Step 2 — Read the type contract, then check for an existing plan

Read `ticket-types/{type}.md`, specifically its *"What shape the plan takes"* and *"What done means"* sections. They supply this plan's required phases, its forbidden phases, the kind of thing a step delivers, the activity mix, and any estimate adjustment. Everything in Steps 3–11 is shaped by them.

- **No `plan.md` yet, or the user explicitly asked to regenerate it** ("regenerate the plan", "refresh the plan") → continue to Step 3.
- **`plan.md` exists** → do not regenerate it. Skip to Step 12.

### Step 3 — Read the digest and survey existing work

Parse `digest.md` and extract:

- **Title** and **type** (from the heading and the Metadata table)
- **Description** — the TL;DR of the problem or goal; this is the primary input for planning
- **Acceptance Criteria** — the conditions that must be met; use these to derive concrete, actionable steps
- **Related Tickets** — note any child or related ids that may map to separate projects or repositories
- **Attachments** — for each attachment listed, if its description suggests it carries information relevant to planning (a mockup, a log file, a spec document, a diagram), open the downloaded file under the ticket's `raw/` and factor its content into the plan. Rely on the digest's existing description first; only open the file itself when more detail is needed than the digest provides.

Then list the ticket's `artifacts/`. If it exists, a previous run already investigated something. For `planning/`, for each `step-{N}.{M}/`, and for `shared/`, read the `README.md` if present, otherwise skim the artifacts themselves.

Anything measured or established there is evidence, and outranks assumption. Do not plan a step that re-derives a fact an existing artifact already settles — reference the artifact instead. If an artifact contradicts `digest.md`, say so to the user and plan around the measured value, not the stated one.

### Step 4 — Establish the scan roots

Discovery always begins from scan roots. They come from the three sources below, combined into one list in which each directory appears once; compare resolved absolute paths, case-insensitively on Windows. The glossary says how far each kind is trusted: a directory the user gave and the invocation directory are facts about this ticket, while a default scan root, or one found by search, says only where to look.

**The default scan roots, always.** Read the list the ticket's own product uses — `/ticket-setup` saves one at the root, on a namespace or on a product, and the nearest level that sets one wins:

```bash
python "{skills}/ticket-common/ticket.py" scan-roots --in "{product}"
```

`{product}` is Step 1's `product` — the ticket's own, never the session context's. Every directory in `scan_roots` is a scan root on every run; `scan_roots_from` is the file they came from, worth naming in Step 6. Skip one that no longer exists, with a one-line note.

**Directories the user gave**, on the invocation or earlier in the conversation. Each is a scan root: do not second-guess it, drop it, or swap it for another worktree of the same repository. If one does not exist, say so and ask for a correction rather than guessing a nearby directory. When the user gave directories, the invocation directory adds nothing.

**The invocation directory**, only when the user gave no directories. Take the first rule that applies:

1. **It is the tickets home** (`paths.tickets_home` from Step 1, or anywhere beneath it) **or the user's home directory itself.** It adds nothing. This rule comes before the next one because a home directory is sometimes a repository of dotfiles.
2. **It is inside a repository** (`git rev-parse --show-toplevel` succeeds). It is a scan root.
3. **It is outside every repository but holds source code**: its top few levels contain a file from [`STACK-HEURISTICS.md`](./STACK-HEURISTICS.md) → *Project signals*, source files, or repositories. It is a scan root.
4. **Otherwise** it holds no source code (documents, downloads, configuration only) and adds nothing.

**Ask only when there is nowhere to look**: the list is empty, or Step 5 finds nothing matching the digest beneath the default scan roots and no other scan root was given.

Say why there is no code to plan against — no default scan roots are saved and the invocation directory holds none, or nothing beneath the default scan roots matches — and ask which directories hold it: a repository's worktree, or a directory holding several repositories. Offer to search if the user is not sure.

Where no default scan roots are saved, add that `/ticket-setup` can save them — for this ticket's namespace or product — so the question does not come up again. Wait for the answer. Any directory it names counts as a directory the user gave.

**If the user cannot name one, search.** Keep the search bounded: never walk the whole home directory or a drive.

1. From `digest.md`, collect distinctive identifiers: named projects, repositories, packages, namespaces, endpoints, tables or collections. Common words match everything and settle nothing.
2. Look for repositories up to three levels beneath whichever conventional code directories exist in the home directory: `source`, `src`, `repos`, `code`, `projects`, `dev`, `git`, `workspace`.
3. Rank each repository by how many identifiers its name, remote URL and top-level project names match.
4. Take the best-ranked as scan roots found by search. Step 6 presents them with the evidence for each, and its confirmation is what turns them into facts.

If nothing matches, report the directories searched and the identifiers tried, and stop. A plan that cannot name a real file is not worth writing.

### Step 5 — Discover the workspace

A ticket's workspace can span several repositories and plain directories. Map it, beginning at the scan roots. Use only read-only git commands (`rev-parse`, `worktree list`, `remote get-url`, `branch --show-current`), and do **not** read source file contents at this stage: file names, paths and directory structure are enough. Build and deployment files may be read, but only for references that point outside their own repository.

**Repositories.** Record the repository holding each scan root, and each repository beneath one, once each however many scan roots reach it. Name each as the glossary says: from its remote's URL, or from its main worktree's directory name where it has no remote.

A repository holding a directory the user gave or the invocation directory is kept regardless. Every other repository is ranked against the digest's identifiers as the search in Step 4 does, and carried forward only when it matches: that covers everything reached only through a default scan root, and each repository beneath a directory of repositories the user named.

**Worktrees.** Run `git worktree list --porcelain` in each repository, skipping entries git marks `prunable`. The workspace holds only the worktrees the work happens in, one or several per repository; a ticket that lands on more than one branch, such as a fix on `main` backported to a release branch, needs a worktree for each:

- Every worktree holding a scan root is in the workspace.
- Otherwise, for a related repository or a directory holding several worktrees of one, list each worktree with its branch and ask in Step 6 which ones the work will happen in. A branch that names this ticket is a sensible default to propose, never one to assume.

Where a worktree left out of the workspace sits on a branch that names this ticket, mention it in Step 6 and offer to add it: the work may already be under way there.

**Related repositories.** Follow evidence out of the scan roots, not proximity:

- References that leave the repository: `.gitmodules`, relative project references, `file:` or `link:` dependencies, `pnpm-workspace.yaml` or a `package.json` `workspaces` field, VS Code `.code-workspace` files, compose build contexts, relative paths in pipeline definitions.
- Projects, packages or repositories the digest names that no scan root reaches. Look for them among the directories beside each repository's main worktree. A sibling that merely exists is not in scope; one the digest or a reference points to is.

**Plain directories.** A scan root outside every repository is recorded as a plain directory.

A directory the user gave and the invocation directory stay in the workspace even when nothing else points to them. Following references only adds to the workspace; it never replaces a scan root.

**Projects.** Within each chosen worktree and plain directory, find the projects by the signals in [`STACK-HEURISTICS.md`](./STACK-HEURISTICS.md) → *Project signals*, in order of priority.

Group the projects into categories:

- **Backend** — APIs, microservices, background workers, libraries
- **Frontend** — SPAs, MFEs, portals
- **Database** — migration projects, schema definitions
- **DevOps / Infra** — CI pipelines, IaC, Dockerfiles, Helm charts
- **Contracts / Shared / Common** — shared libraries, NuGet/npm packages, OpenAPI specs

### Step 6 — Present discoveries and confirm with the user

Show the user each scan root and where it came from, each repository with the worktrees it will be analyzed in and why it is in scope, then the projects grouped by category. Put every open worktree question here. For example:

```
Scan roots
  • C:\src              default scan root
  • C:\src\billing-api  invocation directory

Repositories
  • billing-api        C:\src\billing-api          main worktree · feat/18159-invoice-export
      holds the invocation directory
  • invoice-portal     C:\src\invoice-portal       main worktree · main
      matches "invoice export" and "InvoicePortal" from the digest
  • shared-contracts   C:\src\shared-contracts     main worktree · main
      referenced by src/Api/Billing.Api.csproj in billing-api
      also has a linked worktree at C:\src\wt\shared-contracts-v2 on release/2.0. Should the work happen there too?

Backend
  • billing-api: src/Api/Billing.Api.csproj           (.NET 8 Web API)
  • billing-api: src/Worker/Billing.Worker.csproj     (.NET 8 background service)

Contracts / Shared / Common
  • shared-contracts: src/Contracts/Contracts.csproj  (NuGet package)

Database
  • billing-api: src/Migrations/                      (EF Core migrations)

DevOps / Infra
  • billing-api: .github/workflows/ci.yml

Does this look correct? Are there any repositories, worktrees or projects I missed or should ignore?
```

Where a scan root was found by search, say so on its line and show the identifiers each repository matched.

Wait for the user's response before continuing.

If the user corrects or adds a directory, treat it as a directory the user gave in Step 4: map only that directory as Step 5 does, with its repository, worktrees and projects, then fold it in. Do not re-scan what is already confirmed.

If the user confirms with no changes, proceed.

### Step 7 — Analyze relevant projects

For each confirmed project that is relevant to the description and acceptance criteria, do a **targeted read** in each worktree confirmed for it in Step 6, never in a worktree the workspace does not hold. Read enough to identify:

- The entry point or main module
- Key directories (controllers, services, components, routes, etc.)
- Existing patterns (naming conventions, directory structure, test locations)
- Files most likely to be touched based on the description and acceptance criteria

The goal is to be able to name specific files and classes in the plan. Read only what is necessary — never a whole repository.

### Step 8 — Research unknowns that would change the plan

A plan built on a false assumption is wrong in its *shape*, not just its estimates: phases get sequenced around a bottleneck that is not there, and the effort lands on the wrong candidate. Research is how the plan earns its structure.

Before estimating, name the facts the plan's shape rests on that neither `digest.md` nor the workspace settles — a production row count, whether an index exists, which of two code paths actually runs, the true size of a data set, how long something currently takes. For each, ask: **if this turned out to be wrong by an order of magnitude, would the plan change?** If not, record it as a stated assumption in the plan and move on. If it would, research it now rather than discovering it during implementation.

Reading files needs no permission — a file in the workspace, a local export, an attachment. Writing a script does not need permission either. **Running one always does.**

A script artifact is never executed until the user has approved that specific script. Write it first, then show what it does, what it reads, and where its output will land, and ask:

> To size Phase 2 I need the real number of `UserAuthorization` documents in production — the ticket states ~21,000 but nothing has confirmed it. I have written a read-only query at `artifacts/planning/count-authorizations.js`; it runs one `countDocuments` against `analytics-svc-userauthorizations` and writes nothing. May I run it against production?

- **Approved** → run it. Ask again for each later run — approval covers the run in front of the user, not the script forever.
- **Declined** → do not run it. Record the fact as a stated assumption in the plan, as for a fact that would not change the plan.

Never write to an external system under any circumstance.

Store everything the research produced under `artifacts/planning/`, following `ticket-common/ARTIFACTS.md`: the script, its captured output named for the format it holds, and a `README.md` recording what was asked, what was measured, and what it settled. Then plan against the measured value, and name the artifact on the `**Artifacts:**` line of every step that rests on it.

If research contradicts `digest.md`, plan around the measured value and tell the user which stated fact it displaced — do not quietly plan against a number the ticket still asserts.

### Step 9 — Derive hour estimates

Estimate effort per phase using the baselines and adjustments in [`STACK-HEURISTICS.md`](./STACK-HEURISTICS.md) → *Estimate baselines*. Estimates are rough guides, not commitments. Write every estimate with `~`.

Then apply whatever estimate adjustment `ticket-types/{type}.md` names, and any cap it imposes. A type's adjustment is on top of these, not instead of them.

### Step 10 — Assign an Activity Type to each phase

Every phase must declare exactly one **Activity** from the following fixed set:

| Activity      | Use when the phase is primarily...                                               |
| ------------- | -------------------------------------------------------------------------------- |
| Development   | writing or modifying source code (backend, frontend, scripts)                    |
| Testing       | authoring or updating unit, integration, or E2E tests                            |
| Design        | defining schema, API contracts, or architecture before code is written           |
| Deployment    | CI/CD pipeline changes, IaC, release/rollout steps                               |
| Documentation | README, ADRs, comments, or other written artifacts                               |
| Human Review  | a checkpoint requiring manual approval/decision rather than autonomous execution |

This set is this plan's own taxonomy — nothing is ever written back to any ticket source with these values, so no source may extend or rename them. A type file selects from this set, and may forbid a value; it never adds one.

If a phase's work spans more than one activity, assign the activity that represents the majority of the effort. If the split is significant, divide the work into separate phases instead.

### Step 11 — Write plan.md

Compose the plan using the template and write it to the resolved `plan` path.

Report in one line that the plan was written, with its path. Do not print the plan body in chat.

#### Phase ordering

Order phases by logical dependency — each phase must be completable before the next begins. Within that dependency chain, also order phases by their Activity Type, following the natural execution lifecycle: Design → Development → Testing → Documentation → Deployment. A Human Review phase is a checkpoint, not a lifecycle stage — place it immediately after the phase(s) whose output it gates, wherever that falls in the sequence.

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

Where the type file requires a phase, it comes first regardless of this ordering — a characterization or a reproduction phase exists precisely to run before anything else. Where the type file forbids a phase or an Activity value, that prohibition wins over this list. And where the type file says a plan of this kind is normally a single phase, do not invent phases to fill the template.

#### Plan template

Read [`plan-template.md`](./plan-template.md) and use it as the structure for the output file. Fill every `{camelCase}` placeholder, and replace every `<!-- guidance -->` comment with the content it asks for.

Rules for the template:

- Every step is its own markdown sub-section under `## Phase {N}`, headed `### Step {N}.{M}` (the phase number, a dot, and the step number within that phase, starting at 1), followed by a `**Status:**` line, a `**Target:**` line naming the file/class or the artifact the step delivers, and an `**Artifacts:**` line
- The Workspace section records the workspace confirmed in Step 6. **Scan roots** lists each one and where it came from. **Worktrees** has one row per worktree, so a repository appears once for each of its worktrees in the workspace: its repository, its branch, whether it is `main` or `linked`, and its absolute path. **Plain directories** has one row per plain directory, with its absolute path; omit it when there are none. **Projects** has one row per project in each worktree or plain directory it lives in: its name, where it lives, its path relative to there, and its technology. Worktrees and plain directories are referred to as the glossary says: a worktree by its repository's name, or as `{repository}@{branch}` where the workspace holds more than one worktree of that repository, and a plain directory by its directory name
- A `**Target:**` path is relative to its project's worktree or plain directory. When the workspace holds more than one, name which after the path — `` `src/Invoices/InvoiceService.cs` in `billing-api@release/2.0` `` — since the path alone is ambiguous
- The `**Artifacts:**` line follows `ticket-common/ARTIFACTS.md`. Planning fills it in with the artifacts from Step 8 and with any existing directory for that step; `ticket-implement` appends what it produces
- The Progress table sits at the top, immediately after the header, so it is the first thing visible when opening the file; it is updated alongside the phase step statuses on subsequent runs
- Every row's Phase cell links to that phase's own section — `{phaseAnchor}` in the template — `[Phase 1: Database migration](#phase-1-database-migration-05-hrs)`, and `[Prerequisites](#prerequisites)` for the prerequisites row. The anchor is the GitHub slug of the full `##` heading, estimate included: lowercase it, drop every character that is not a letter, digit, space or hyphen, then turn spaces into hyphens — `## Phase 1: Database migration (~0.5 hrs)` → `#phase-1-database-migration-05-hrs`. A phase renamed, renumbered, or re-estimated has its heading and its link changed together; drop the Prerequisites link where that section is omitted
- Each phase's `**Activity:**` line must use exactly one value from the Activity Type set defined in Step 10; the Progress table's Activity column for that phase must match
- `{ticketUrl}` is `ticket.json`'s `url`. **Where it is `null`, write the title as plain text rather than a broken link.** For any other reference, use the patterns in `ticket-providers/{source}/links.md`
- Omit the Prerequisites section if it has no content

#### Step status

The four-value vocabulary, the note rules, and the table deriving a phase's Progress row from its steps are in `ticket-common/STATUS.md`. Read it rather than restating it.

`Pending` and `Done` are the only two statuses a freshly generated plan may use — nothing has been started yet, so nothing can be in progress or blocked.

Stop.

### Step 12 — Read and summarize current progress

Read `plan.md` and list the ticket's `artifacts/`. Reconcile the two: if a step has an artifacts directory but its `**Artifacts:**` line still reads `—`, fill the line in. Then recompute each phase's Progress table row from its steps' `**Status:**` lines, using the derivation table in `ticket-common/STATUS.md`, and repair any Phase cell whose link is missing or no longer matches its heading.

Print a compact summary table in chat. Head it with the ticket's qualified reference and title:

```
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

### Step 13 — Ask which phase to update

Ask the user:

> Which phase or step would you like to update? Name a phase or step (e.g. "Step 2.1") and its new status — done, in progress, or blocked — or ask me to research an open question, or say "none" to exit.

Wait for the response.

### Step 14 — Update plan.md

Based on the user's answer:

- If they name a **phase** with no status, or say it is complete: set `**Status:** Done` on every step sub-section within that phase section and update the Progress table row to `[x] Done`
- If they name a **specific step**: set its `**Status:**` to the status they gave, defaulting to `Done` when they gave none, then recompute the phase's Progress table row from the derivation table in `ticket-common/STATUS.md`
- If the new status is `In Progress` or `Blocked`, a note is required. Take it from what the user said; where they gave none, ask for the step's one-line note rather than writing a bare status: for `In Progress`, what is done and what remains; for `Blocked`, what is blocking and what would clear it.
- If they ask to **research** something (e.g. "find out whether that index exists"): run Step 8 for that question alone, store what it produces under `artifacts/planning/`, then revise only the steps the finding actually affects — their prose, their estimate, and their `**Artifacts:**` line. Leave every other step's content as it is. If the finding changes the plan's shape, renumber and complete the rename in one pass (see `ticket-common/ARTIFACTS.md`). Report what changed and what it displaced
- Update the Progress table to reflect the new state — the status column, plus the Phase cell's link wherever a heading was renamed, renumbered, or re-estimated
- If they say "none" or similar, exit without changes

Report in one line that `plan.md` was updated, with its path.
