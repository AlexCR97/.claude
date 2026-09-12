# Artifacts

Read by `ticket-plan` and `ticket-implement`. Everything a run produces that is not a change to the codebase lives under one directory per ticket, laid out the same way for every source and every type.

```
{ticket-dir}/artifacts/
├── planning/          ← research done to build the plan itself
├── shared/            ← artifacts spanning more than one step
└── step-{N}.{M}/      ← everything one plan step produced
```

`artifacts/` and its subdirectories are created lazily — only when a run actually produces a file. The ticket root holds nothing but its six entries: **never write a generated file directly into `{ticket-dir}/`.**

Nothing here belongs in the repository being worked on. An artifact is a record of how this ticket was investigated, not a deliverable — never copy one into the codebase unless a plan step explicitly says to.

---

## Placement

- A file belongs to the step that produced it: `artifacts/step-{N}.{M}/`, where `{N}.{M}` matches the `### Step {N}.{M}` heading in `plan.md` exactly.
- A file produced while researching the plan itself — before the steps it informs exist — goes in `artifacts/planning/`.
- A file that more than one step reads, or that applies to the plan as a whole (a findings document, a data extract several steps consult), goes in `artifacts/shared/`.
- The captured output of running a script is written beside it as `{name}.output.{ext}`, where `{ext}` is the format the output actually is — `.json` for a JSON document, `.csv`, `.tsv`, `.jsonl`, `.md`, `.sql`, `.xml`, and so on. **Default to `.txt`**, and reach for a structured extension only when the whole file parses as that format: console output that mixes a table, a log line and a summary is `.txt`, however much JSON it happens to contain. Naming a capture for what it holds is what lets a later run parse it instead of re-running the script to get the data in a usable shape.
- When a structured capture would be spoiled by diagnostics, keep stdout in the structured file and put stderr beside it as `{name}.stderr.txt`. Where output is plain text anyway, one combined `{name}.output.txt` is simpler and preferred.
- Any of these directories may hold a `README.md` recording what was done and what it found. Write one whenever the artifacts alone would not tell a later reader why they exist.

### Who writes where

| Directory | Written by | Read by |
| --- | --- | --- |
| `planning/` | `ticket-plan` only | both |
| `shared/` | `ticket-implement` | both |
| `step-{N}.{M}/` | `ticket-implement` | both |

`ticket-plan` reads `planning/` to avoid re-deriving what a previous run settled. `ticket-implement` reads `planning/` to see *why* a step is shaped the way it is, and never writes to it.

---

## Artifacts are append-only

A measurement taken against a live system is the one thing here that cannot be regenerated. Never delete or overwrite an existing artifact — write a new file alongside it instead. Renaming a step directory during a renumbering pass is not a deletion, and is expected.

Never re-run a probe whose captured output is already on disk.

---

## Renumbering is a rename

Plans change shape: research reorders phases, one step splits into two, a phase turns out to belong earlier. **Renumber whenever the plan reads better for it.** A step number is also a directory name, though, so renumbering is a rename — and it is finished only when nothing still points at the old number:

1. Rename each affected `artifacts/step-{old}/` to `artifacts/step-{new}/`.
2. Update the `## Phase {N}` and `### Step {N}.{M}` headings in `plan.md`.
3. Update every `**Artifacts:**` line that named a renamed directory.
4. Search `plan.md` and every file under `artifacts/` — `planning/`, `shared/`, and each step's `README.md` included — for the old identifiers (`step-1.1`, `Step 1.1`, `Phase 3`) and update each occurrence.
5. Tell the user what moved and why.

Do all five in one pass. A half-renumbered plan, where an `**Artifacts:**` line points at a directory that no longer exists, is worse than one that was never renumbered at all.

---

## The `**Artifacts:**` line

Every step carries one. It names every file the step **produced or rests on**, as paths relative to `plan.md`:

```
**Artifacts:** [artifacts/planning/count-authorizations.output.json](artifacts/planning/count-authorizations.output.json)
```

It reads `—` only when a step neither produced anything nor depends on prior research. A step that produced files must name them, and a path it names must exist.

Cite a research artifact on the `**Artifacts:**` line of every step whose estimate or approach depends on it — research nothing cites was not worth doing.

---

## Running a script is always a separate permission

Writing a script artifact needs no permission. **Running one always does**, every time, for every script. Write it first, then show what it does, what it reads, and where its output will land, and ask. Approval covers the run in front of the user, not the script forever.

A plan step authorizing the *work* is not authorization to *execute* a script that step happens to produce — the plan was written before the script existed. Build commands are not script artifacts and are unaffected by this rule.

Script artifacts must be **read-only** with respect to any external system they touch. A probe that reads a production database is in scope; anything that writes to one is a change to the environment and is not.

If what an artifact establishes contradicts the plan, do not quietly implement the plan anyway. Record the contradiction in the artifact, tell the user, and ask whether to revise the plan before continuing.
