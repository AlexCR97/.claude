---
name: ticket-plan
description: Turns a ticket's digest.md into a plan — one file per phase under plan/, joined by a dependency graph showing which phases can run in parallel. Discovers repositories, worktrees and projects from its scan roots, and researches unknowns under artifacts/planning/. Re-run, it updates step status.
argument-hint: "<ref> [dir ...] [--type type]"
---

Turns a ticket's `digest.md` into a plan: one file per phase under `plan/`, each naming the phases it depends on, and an index, `plan/plan.md`, whose generated Progress table and graph show which phases are Ready — so that phases with no path between them can be worked on in parallel, one session each. It discovers the workspace — the repositories, worktrees and projects the work spans — from the ticket's scan roots, researches the facts the plan's shape rests on, and shapes the phases and their dependencies by the ticket's type. Run again on a ticket that has a plan, it shows progress and updates step status. It plans only: research artifacts under `artifacts/planning/` are part of planning — a plan built on an unverified assumption is worth less than the hour spent verifying it — but no change to the workspace is. The terms for code and for the plan mean what `ticket-common/GLOSSARY.md` says; read it before discovering anything.

End state: `plan/` written from `digest.md` and the confirmed workspace — `plan.md` indexing it and one phase file per phase, the graph acyclic and the generated block synced — every research artifact under `artifacts/planning/` cited by the steps that rest on it, and the workspace unchanged; or, on a later run, the phase files updated as the user asked and the block re-synced.

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
5. **Use the glossary's terms exactly**, in the plan and in chat — never a synonym it retires. A unit of planned work is a **phase**, never a task.
6. **Write only `plan/` and `artifacts/planning/`.** `ticket.py plan-renumber` is the one exception: it renames step directories and fixes references under `artifacts/`. `artifacts/step-{N}.{M}/` and `artifacts/shared/` belong to implementation.
7. **Never run a script without approval of that run.** Write it, show it, ask, then run; never run anything that writes to an external system.
8. **Never break the type's rules.** A required phase, a forbidden phase, a dependency rule or an Activity prohibition in the resolved type's file wins over this file.
9. **Never write a bare `In Progress` or `Blocked` status.** Each needs a one-line note.
10. **Never edit the generated block in `plan.md`.** Change the phase files, then run `ticket.py plan-sync`, which rewrites the block from them.
11. **Never renumber or regenerate while any phase is `In Progress`.** Another session may be working that phase, and writing into the very `artifacts/step-{N}.{M}/` directory a rename would move.

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

Read `ticket-types/{type}.md`, specifically its *"What shape the plan takes"* and *"What done means"* sections. They supply this plan's required phases, its forbidden phases, the dependencies between them, the kind of thing a step delivers, the activity mix, and any estimate adjustment. Everything in Steps 3–12 is shaped by them.

- **`on_disk.legacy_plan` is true** — a `plan.md` at the ticket root, in the old single-file format → follow [`MIGRATION.md`](./MIGRATION.md), then continue as it says. <!-- MIGRATION: delete this line with MIGRATION.md. -->
- **No plan yet** (`on_disk.plan` is false) → continue to Step 3.
- **The user explicitly asked to regenerate it** ("regenerate the plan", "refresh the plan") → check first, with `python "{skills}/ticket-common/ticket.py" plan-sync "<ref>" --dry-run`. Where any phase is `In Progress`, refuse: name the phase and its step's note, and say regenerating must wait until no session is working it. Otherwise list every phase holding a `Done` step, whose status the new plan would lose, and ask before going on. On a yes, continue to Step 3; Step 12 replaces the phase files. Artifact directories are left alone.
- **A plan exists** → do not regenerate it. Skip to Step 13.

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

### Step 11 — Cut the phases and draw the graph

Read [`GRAPH-RULES.md`](./GRAPH-RULES.md) and apply it in full before writing anything: it says how to cut the work into phases, where each prerequisite goes, which dependencies to draw, and how to number the phases. A phase is the unit one session works, and the graph between phases is what lets several sessions work at once.

### Step 12 — Write the plan

Write `plan.md` and every phase file into the resolved `plan_dir`, creating it. On a regeneration, the phase files written replace every phase file already there; remove those no longer in the plan. Then sync:

```bash
python "{skills}/ticket-common/ticket.py" plan-sync "<ref>" [--context {context}]
```

It reads every phase file, checks the graph, fills the generated block in `plan.md`, and reports each phase's derived status and readiness. On a non-zero exit, fix the phase files it names and run it again. Act on each of its `warnings` — a shared `**Target:**` means a missing dependency or two phases that should be one — and sync again.

Report in one line that the plan was written, with the path to `plan.md`, how many phases it has, which are Ready now, and the critical path. On a regeneration, also name every artifacts directory no step now points at — orphaned, never deleted. Do not print the plan body in chat.

`Pending` and `Done` are the only two statuses a freshly generated plan may use — nothing has been started yet, so nothing can be in progress or blocked. `ticket-common/STATUS.md` has the vocabulary and the note rules.

Stop.

#### The index — `plan.md`

Read [`templates/plan.md`](./templates/plan.md) and use it as the structure. Fill every `{camelCase}` placeholder, and replace every `<!-- guidance -->` comment with the content it asks for.

- Leave the generated block's two marker lines exactly as the template has them, with nothing between them: `plan-sync` fills it with the Progress table — each phase linked to its file — the dependency graph, the total estimate and the critical path.
- The Workspace section records the workspace confirmed in Step 6. **Scan roots** lists each one and where it came from. **Worktrees** has one row per worktree, so a repository appears once for each of its worktrees in the workspace: its repository, its branch, whether it is `main` or `linked`, and its absolute path. **Plain directories** has one row per plain directory, with its absolute path; omit it when there are none. **Projects** has one row per project in each worktree or plain directory it lives in: its name, where it lives, its path relative to there, and its technology. Worktrees and plain directories are referred to as the glossary says: a worktree by its repository's name, or as `{repository}@{branch}` where the workspace holds more than one worktree of that repository, and a plain directory by its directory name.
- `{ticketUrl}` is `ticket.json`'s `url`. **Where it is `null`, write the title as plain text rather than a broken link.** For any other reference, use the patterns in `ticket-providers/{source}/links.md` — `plan.md` sits one level below the ticket directory.

#### A phase file — `{N}-{slug}.md`

Read [`templates/phase.md`](./templates/phase.md) and use it as the structure for each phase, with the same placeholder rules.

- The file is named `{N}-{slug}.md`: the phase number, then a short lowercase hyphenated slug of its title — `2-repository-layer.md`.
- The frontmatter is the phase's record, in the suite's flat `key: value` subset: `number`, matching the file name; `title`; `activity`, exactly one value from Step 10's set; `estimate`, a number of hours with no `~`; `depends_on`, the numbers of the phases it depends on — `[]` for a root; `projects`, the names of the projects it touches, as the Workspace section's Projects table names them. **No status**: a phase's status is derived from its steps.
- `## Prerequisites` holds only what this phase alone needs, as a `- [ ]` checklist. Omit the section when there is none.
- Every step is its own sub-section, headed `### Step {N}.{M}` — the phase number, a dot, and the step number within that phase, starting at 1 — followed by a `**Status:**` line, a `**Target:**` line naming the file/class or the artifact the step delivers, and an `**Artifacts:**` line.
- A `**Target:**` path is relative to its project's worktree or plain directory. When the workspace holds more than one, name which after the path — `` `src/Invoices/InvoiceService.cs` in `billing-api@release/2.0` `` — since the path alone is ambiguous. Write the same file the same way in every phase that targets it: that is how `plan-sync` spots two phases sharing one.
- The `**Artifacts:**` line follows `ticket-common/ARTIFACTS.md`, its paths relative to the phase file as that file's *The `**Artifacts:**` line* shows. Planning fills it in with the artifacts from Step 8 and with any existing directory for that step; `ticket-implement` appends what it produces.

### Step 13 — Read and summarize current progress

Sync, which re-derives every phase's status and readiness from the phase files and rewrites the block in `plan.md` where it is stale:

```bash
python "{skills}/ticket-common/ticket.py" plan-sync "<ref>" [--context {context}]
```

Then list the ticket's `artifacts/` and reconcile it with the phase files: where a step has an artifacts directory but its `**Artifacts:**` line still reads `—`, fill the line in. Where `plan-sync` reported `warnings`, show them.

Print a compact summary table in chat, from the sync's output. Head it with the ticket's qualified reference and title:

```
| Phase                       | Depends on | Activity    | Estimate   | Status            | Ready        |
| --------------------------- | ---------- | ----------- | ---------- | ----------------- | ------------ |
| Phase 0: Prerequisites      | —          | Deployment  | ~0.5 hrs   | [x] Done          | —            |
| Phase 1: Database migration | 0          | Development | ~0.5 hrs   | [x] Done          | —            |
| Phase 2: Repository layer   | 1          | Development | ~1.5 hrs   | [~] In Progress   | ✅            |
| Phase 3: Portal export page | 0          | Development | ~2 hrs     | [ ] Pending       | ✅            |
| Phase 4: API endpoint       | 2          | Development | ~1.5 hrs   | [ ] Pending       | waiting on 2 |
| **Total**                   |            |             | **~6 hrs** | 2 / 5 phases done | 2 ready      |

Critical path: 0 → 1 → 2 → 4 (~4 hrs)
```

Under the table, list every `In Progress` and `Blocked` step with its note, so the reason a phase is not moving is visible without opening its file — then name the Ready phases not yet started: each can be taken up now, in a session of its own.

### Step 14 — Ask what to update

Ask the user:

> Which phase, step or prerequisite would you like to update? Name a phase or a step (e.g. "Step 2.1") and its new status — done, in progress, or blocked — or a prerequisite now in place; or ask me to research an open question; or say "none" to exit.

Wait for the response.

### Step 15 — Update the phase files

Based on the user's answer, edit the phase files — never the generated block in `plan.md`:

- If they name a **phase** with no status, or say it is complete: set `**Status:** Done` on every step in that phase's file.
- If they name a **specific step**: set its `**Status:**` to the status they gave, defaulting to `Done` when they gave none.
- If the new status is `In Progress` or `Blocked`, a note is required. Take it from what the user said; where they gave none, ask for the step's one-line note rather than writing a bare status: for `In Progress`, what is done and what remains; for `Blocked`, what is blocking and what would clear it.
- If they name a **prerequisite** now in place: check its box, `- [x]`, in the phase that lists it.
- If they ask to **research** something (e.g. "find out whether that index exists"): run Step 8 for that question alone, store what it produces under `artifacts/planning/`, then revise only the steps the finding actually affects — their prose, their phase's estimate, and their `**Artifacts:**` line. Leave every other step's content as it is. Report what changed and what it displaced.
- If the finding changes the plan's **shape** — a phase splits, merges, or gains or loses a dependency — apply `GRAPH-RULES.md` to the phases it touches and edit their files, then renumber where the order no longer holds, as below.
- If they say "none" or similar, exit without changes.

**Renumbering.** Once every phase file is edited, check whether the numbers still run in topological order, and decide the order `GRAPH-RULES.md` → *Numbering* gives. Show the user what would move:

```bash
python "{skills}/ticket-common/ticket.py" plan-renumber "<ref>" --order {N,N,...} --dry-run [--context {context}]
```

`--order` lists the current numbers of every phase after `0`, in their new order; the script checks it against the graph. Without `--order`, it keeps the current order wherever the graph allows. On a yes, run it again without `--dry-run`: it renames the phase files and `artifacts/step-*` directories and rewrites every reference in one pass, as `ticket-common/ARTIFACTS.md` → *Renumbering is a rename* describes. Where it refuses because a phase is `In Progress`, keep the current numbers — gaps and out-of-order numbers are tolerated until a later run — and say so.

Then sync, as Step 13 does, and report in one line that the plan was updated, with the path to `plan.md` and every phase whose readiness changed.
