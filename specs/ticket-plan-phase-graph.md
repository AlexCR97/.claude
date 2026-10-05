# Spec — ticket-plan: phases as files, joined by a dependency graph

Status: implemented · 2026-10-05

## Goal

`ticket-plan` stops writing one monolithic `plan.md`. It writes one file per phase, and records a dependency graph between the phases, so that any phase whose dependencies are done can be worked on in parallel with the others.

## Out of scope

- **Running phases in parallel automatically.** The graph is information only: the developer opens one session per phase they want to run concurrently. No subagent fan-out from `ticket-implement`.
- **A worktree per phase**, and any git operation. The suite still never runs git.

---

## Decisions

### 1. A phase stays the unit of work

A phase keeps its steps, its estimate and its Activity, and is cut so it can be implemented, built and verified on its own. Steps survive as the checklist inside a phase. The term stays **phase** — not task.

**Why:** the unit of parallel work has to build on its own. A single step often does not compile in isolation, so a graph of steps would be dense with compile-only edges and offer little real parallelism.

### 2. Layout: a `plan/` directory

```
{ticket-dir}/plan/
├── plan.md                  ← the index
├── 0-prerequisites.md       ← only when prerequisites are shared
├── 1-database-migration.md
├── 2-repository-layer.md
└── 3-api-endpoint.md
```

- Phase numbers are **one digit**, everywhere: `1-database-migration.md`, `Step 3.2`, `artifacts/step-3.2/`. Past nine phases a raw directory listing sorts `10-…` before `2-…`; accepted, since the Progress table is ordered by the script.
- `plan/` replaces `plan.md` among the ticket directory's entries — update `GLOSSARY.md`, `ARTIFACTS.md`, `WORKFLOW.md` and `ticketlib/paths.py`.
- The resolver's `plan` path becomes `{ticket-dir}/plan/plan.md`, and it gains `plan_dir`. `--require plan` checks `plan/plan.md` exists.

### 3. Relative paths are relative to the file they are written in

- `plan.md` links `../digest.md`, `../journal.md`, `../raw/{file}`, and each phase as `{N}-{slug}.md`.
- A phase file's `**Artifacts:**` line reads `../artifacts/step-3.2/…`; it links back to the index as `plan.md`.
- `ticket-providers/ado/links.md` and `ticket-providers/local/links.md` currently say `plan.md` sits in the ticket directory — update both.

### 4. Phase files are the source of truth

Frontmatter uses the existing stdlib-only subset the local provider already parses — flat `key: value` pairs and `[a, b]` lists, no YAML library:

```
---
number: 3
title: API endpoint
activity: Development
estimate: 1.5
depends_on: [1, 2]
projects: [Billing.Api]
---
```

- **No `status` field.** A phase's status is derived from its steps' `**Status:**` lines, by the table in `ticket-common/STATUS.md`. Storing it as well would let the two drift.
- Body: **Scope**, an optional `## Prerequisites` checklist (`- [ ] …`) for prerequisites only this phase needs, then `### Step {N}.{M}` sections with `**Status:**`, `**Target:**` and `**Artifacts:**` lines, as today.

### 5. `plan.md` is an index with a generated block

`plan.md` holds the header, the Workspace section, and a **generated block** that a new `ticket.py plan-sync` rewrites in full by reading every phase file. Every skill that changes a status calls `plan-sync` afterwards; none edits the block by hand.

The generated block holds:

- a **Progress table** — Phase (linked to its file) · Depends on · Activity · Estimate · Status · Ready
- a **Mermaid flowchart** of the graph, nodes styled by status
- the **total effort**, and the **critical path** — the longest dependency chain by estimate, the floor on wall-clock time with unlimited parallel sessions

**Why:** several sessions on one ticket would race to hand-edit one Progress table. Regenerating the whole block from the phase files means whichever session syncs last writes the correct state.

### 6. Phase `0` — shared prerequisites

- A prerequisite only one phase needs lives in that phase's `## Prerequisites`.
- A prerequisite **two or more phases share** gets phase `0`, `0-prerequisites.md`. It is an ordinary phase: usually a single step, an estimate of at most ~1 hr, and the closest Activity from the existing set — usually **Deployment**, or **Human Review** where the item is a decision or an approval. No new Activity value is added.
- Only the phases that need it depend on it, not every root.
- `0` is reserved: renumbering starts at `1` and never moves it. A plan with no shared prerequisites has no phase `0`.

### 7. The graph

- **An edge means a hard dependency.** B depends on A only when B cannot be written or built without A's output — a schema, contract, type or endpoint it consumes. A sensible order ("tests after code") is not an edge unless the tests exercise that code.
- **Overlapping phases must be ordered or merged.** Two phases with no path between them are claimed parallel-safe; if they edit the same file, add an edge or merge them.
- **Ready is derived, never stored:** every dependency `Done` **and** every prerequisite checked. The Ready column says why a phase is not ready — `waiting on 2`, `2 prerequisites open`.
- **`Blocked` keeps its meaning** — something outside the graph, with a required note. A phase waiting on an unfinished dependency is not `Blocked`; one depending on a `Blocked` phase is simply waiting.

### 8. Type files speak in graph terms

Each `ticket-types/{type}.md` → *What shape the plan takes* is reworded so its ordering rules become graph rules — e.g. bug: "the reproduce phase is a root every code-changing phase depends on"; tech-debt: "every restructuring phase depends on the characterization phase". Step 11's lifecycle list in `ticket-plan` stops being a sequence and becomes guidance for drawing edges — e.g. "a phase that consumes a schema depends on the phase that defines it".

### 9. Numbering follows topological order

- Phases are numbered in topological order. Ties between phases with no path between them break by lifecycle order — Design → Database → Backend → Shared → Frontend → Tests → Docs → DevOps — then by estimate, larger first.
- A new **`ticket.py plan-renumber`** performs the whole rename mechanically — phase files, headings, `depends_on`, `artifacts/step-*` directories, and references under `artifacts/` — then runs `plan-sync`. This replaces the five-point manual pass in `ARTIFACTS.md` → *Renumbering is a rename*.
- **Only `ticket-plan` renumbers**, on regeneration or when research changes the graph, and it **refuses while any phase is `In Progress`** — another session may be writing into `artifacts/step-3.1/` at that moment. It says why and offers to keep the current numbers; gaps and out-of-order numbers are tolerated until a later run.

### 10. Regenerating the plan

Refused while any phase is `In Progress`. Otherwise, list every phase with a `Done` step whose status would be lost and ask before replacing the phase files. Artifact directories are left alone; a step that no longer exists leaves an orphaned directory, which the summary reports and never deletes — artifacts are append-only.

### 11. `ticket-implement`

- **`<ref> [phases | all]`** stays; `all` means every phase not `Done`, run sequentially in this session in number order. With no argument, show the Progress table with its Ready column and ask.
- **Dependencies not done:** warn, naming what the phase is waiting on, and ask — the developer may know better, e.g. the dependency is finished in another worktree.
- **Phase already `In Progress`:** never resume silently. Say "phase 3 is In Progress (*note*) — another session may own it. Resume here?" and wait.
- **Prerequisites:** list the phase's unchecked prerequisites up front, ask whether each is in place, and tick the ones confirmed.
- **Shared builds:** a build error in a file this phase did not touch is not fixed — report it as likely another session's work in flight, and stop the phase without marking it `Done`.
- Writes step status to the phase file, then calls `plan-sync`.

### 12. `ticket-checkpoint` and `ticket-resume`

- One `journal.md` stays. Each entry names the phase(s) the session worked; `ticket-checkpoint` re-reads the file immediately before inserting, so two sessions checkpointing close together do not clobber each other.
- `ticket-checkpoint` corrects stale step statuses in phase files, then calls `plan-sync`.
- `ticket-resume` briefs every in-flight phase and offers the Ready phases as candidate next actions.

### 13. `ticket-plan` re-run (Steps 12–14)

Status updates are written to phase files, then `plan-sync` runs. Research that changes the graph follows decision 9.

---

## Migration — temporary

Existing tickets have a phased `plan.md` at the ticket root. They are converted once, not supported indefinitely.

**Detection:** `plan.md` at the ticket root, no `plan/` directory.

**Other skills:** the resolver's `--require plan` fails on the old format with the hint *run /ticket-plan to convert*, so the check lives in one place.

**Conversion,** offered by `ticket-plan`, with the logic isolated in `ticket-plan/MIGRATION.md` and referenced from `SKILL.md` by one marked line:

1. Each `## Phase N` becomes `plan/{N}-{slug}.md`, its Scope, Activity, estimate, steps, statuses and `**Artifacts:**` lines carried over verbatim. Step numbers do not change, so **no artifact directory moves**; only the `**Artifacts:**` paths gain `../`.
2. Edges default to a linear chain — N depends on N−1 — which is exactly the old meaning. Then offer to re-derive the real edges under decision 7; doing so may renumber, under decision 9.
3. The old plan-wide Prerequisites section becomes phase `0`, and phase `1` depends on it.
4. `plan.md` moves into `plan/`, is rewritten as the index, its links fixed, and `plan-sync` generates its block.

**Removal:** once every plan is converted, delete `ticket-plan/MIGRATION.md`, the line in `ticket-plan/SKILL.md` that references it, and the old-format check in the resolver. A memory entry records this follow-up.

---

## Affected files

| Area | Files |
| --- | --- |
| `ticket-plan` | `SKILL.md`, `plan-template.md` (index), new phase template, new `MIGRATION.md`, `EXAMPLE.md` |
| Other drivers | `ticket-implement/SKILL.md`, `ticket-checkpoint/SKILL.md`, `ticket-resume/SKILL.md` (+ their `EXAMPLE.md`, `briefing.md`, `journal-template.md` where they mention phases or `plan.md`) |
| Shared contracts | `ticket-common/STATUS.md`, `ARTIFACTS.md`, `GLOSSARY.md`, `WORKFLOW.md`, `RESOLUTION.md` |
| Types | `ticket-types/{bug,spike,task,tech-debt,user-story}.md` → *What shape the plan takes* |
| Providers | `ticket-providers/ado/links.md`, `ticket-providers/local/links.md` |
| Resolver | `ticketlib/paths.py`, `ticketlib/tickets.py`, `ticket.py` — `plan/` paths, `plan_dir`, old-format check, `plan-sync`, `plan-renumber` |
| Memory | follow-up to remove the migration |

---

## Implementation notes

Where the implementation settled something the decisions above left open:

- **Tie-breaks are the planner's judgment, not the script's.** The script cannot tell a Database phase from a Backend one — both are Development — so `plan-renumber --order N,N,…` takes the order `ticket-plan` decided and checks it against the graph. Without `--order`, it keeps the current relative order wherever the graph allows.
- **`plan-renumber` itself refuses** while a phase is `In Progress`, not only `ticket-plan`'s instructions.
- **A `Blocked` phase is never Ready**, even with every dependency `Done`: what blocks it lies outside the graph.
- **Overlap is detected from `**Target:**` lines.** `plan-sync` warns when two phases with no path between them share one, so targets must name a file the same way everywhere.
- **A phase file's body carries no Activity or estimate** — both live only in frontmatter, so they cannot drift apart. The `# Phase {N}: {title}` heading carries the number, which `plan-renumber` rewrites.
- **`plan-renumber` never rewrites a captured output** (`*.output.*`, `*.stderr.*`) — measurements stay as recorded.
- **A build failure only in files a phase did not touch** sets that phase's last step `Blocked`, with a note naming the file, rather than leaving it `In Progress`.
- **The frontmatter parser moved to `ticketlib/frontmatter.py`**; the local provider's `_store.py` now imports it instead of keeping its own copy.
- **The glossary retires "task"** for a unit of planned work, and **"blocked"** for a phase merely waiting on a dependency.
