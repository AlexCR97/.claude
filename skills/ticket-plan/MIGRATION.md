# Converting a single-file plan

**Temporary.** Plans used to be one `plan.md` at the ticket root, its phases as `## Phase {N}` sections run in strict order. They are now a `plan/` directory with one file per phase and a dependency graph between them. This file converts an old plan, once, when `ticket-plan` finds one.

**Remove it once no old plan is left.** Check with:

```bash
python -c "import pathlib; print(*pathlib.Path.home().joinpath('.tickets').glob('*/*/*/*/plan.md'), sep='\n')"
```

When that prints nothing, delete this file and every line marked `MIGRATION:` — in `ticket-plan/SKILL.md` (Step 2), `ticket-common/RESOLUTION.md`, and `ticket-common/ticketlib/` (`paths.py`, `tickets.py`, `sources.py`).

---

## When it applies

The resolver reports `on_disk.legacy_plan: true`: a `plan.md` at the ticket root and no `plan/plan.md`. Every other skill refuses such a ticket, its `--require plan` hint pointing here.

## Step 1 — Offer the conversion

Say the plan is in the old single-file format, that `ticket-implement`, `ticket-checkpoint` and `ticket-resume` can no longer read it, and what converting does: one file per phase, every step, status and artifact kept as it is, and phases chained in their old order. Ask before converting.

- **Declined** → stop. Nothing changes.
- **Approved** → continue.

## Step 2 — Write one phase file per phase

Read the old `plan.md` in full. For each `## Phase {N}: {name} (~{hours} hrs)` section, write `plan/{N}-{slug}.md` from [`templates/phase.md`](./templates/phase.md):

- **Frontmatter:** `number: {N}`; `title`, the phase name; `activity`, from its `**Activity:**` line; `estimate`, the hours from its heading, without `~`; `projects`, from its `**Projects touched:**` line, as names; and `depends_on: [{N-1}]` — or `[]` for phase 1, or `[0]` where Step 3 writes a phase `0`. A chain is exactly what the old order meant, so nothing becomes parallel that was not before.
- **Body:** the `**Scope:**` line, then every step **verbatim** — its heading, `**Status:**` with its note, `**Target:**`, and prose. Carry over any other prose the section held.
- **`**Artifacts:**` lines** gain one `../`, since the phase file sits one level below the ticket directory: `artifacts/step-2.1/…` becomes `../artifacts/step-2.1/…`.

Phase and step numbers do not change, so **no artifact directory moves**.

## Step 3 — Turn the old Prerequisites into phase 0

Where the old plan had a `## Prerequisites` section with at least one item, write `plan/0-prerequisites.md`:

- `number: 0`, `title: Prerequisites`, `estimate` at most `1`, `depends_on: []`, and the closest Activity — usually `Deployment`, or `Human Review` where the items are decisions or approvals.
- One step, `### Step 0.1`, whose prose is the old checklist, carried over as it was. Its status is `Done` where every item was checked, `Pending` otherwise.

Phase 1 then depends on it, which matches the old meaning: the prerequisites came before any phase began.

## Step 4 — Move the index

Write `plan/plan.md` from [`templates/plan.md`](./templates/plan.md), carrying the old header and Workspace section over unchanged except for links: `digest.md`, `journal.md` and anything under `raw/` gain one `../`. Leave the generated block empty. Drop the old Progress table, Prerequisites section and phase sections — the phase files hold them now. Then delete the old root `plan.md`.

## Step 5 — Sync

```bash
python "{skills}/ticket-common/ticket.py" plan-sync "<ref>" [--context {context}]
```

On a non-zero exit, fix the phase files it names. The chain makes every phase depend on the one before, so `plan-sync` reports no overlap warnings yet.

## Step 6 — Offer real dependencies

The chain is safe but runs nothing in parallel. Offer to re-derive the real dependencies by [`GRAPH-RULES.md`](./GRAPH-RULES.md) → *Drawing dependencies*, from each phase's steps and targets. On a yes, edit each `depends_on`, sync, and act on any overlap warning. Where the numbers no longer run in topological order, renumber as `SKILL.md` Step 15 → *Renumbering* says — which refuses while a phase is `In Progress`, and keeping the current numbers is fine.

Report in one line that the plan was converted, with the path to `plan/plan.md`, how many phase files were written, and which phases are Ready. Then continue with `SKILL.md` Step 13.
