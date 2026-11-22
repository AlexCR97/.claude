# Artifacts

Everything a run produces that is not a change to the workspace lives under the ticket directory's `artifacts/`. An artifact is a record of how the ticket was investigated, never a deliverable: it is not copied into a repository unless a plan step says to. Nothing generated is written directly in the ticket directory.

```
{ticket directory}/artifacts/
├── planning/        research done to build the plan; written by `plan`
├── shared/          artifacts more than one step reads; written by `implement`
└── step-{N}.{M}/    everything one plan step produced; written by `implement`
```

Directories are created when a run first needs one. `implement` reads `planning/` to see why a step is shaped as it is and never writes to it. A step's directory number matches its `### Step {N}.{M}` heading, so renumbering a step renames its directory and every path in `plan.md` that names it.

## Rules

- **Append-only.** A measurement taken against a live system cannot be regenerated. Never delete or overwrite an artifact: a later run writes a new file alongside. Never re-run a probe whose captured output is on disk.
- **Captures are named by the format they hold.** A script's output is written beside it as `{name}.output.{ext}`: `.json`, `.csv`, `.md` and so on only when the whole file parses as that format, otherwise `.txt`. Where diagnostics would spoil a structured capture, keep them in `{name}.stderr.txt`.
- **A `README.md`** in any of these directories records what was done and what it found, wherever the files alone would not tell a later reader why they exist.
- **Cite what a step rests on.** A step's `**Artifacts:**` line names every artifact it produced or depends on, relative to `plan.md`, and each must exist.
- **A finding that contradicts the plan** is recorded in the artifact and shown to the user, who decides whether the plan changes; it is never quietly ignored.

## Running a script

Writing a script needs no permission. Running one needs it unless the script only reads ([ADR 0002](../docs/adr/0002-read-only-scripts-run-without-approval.md)).

Every script opens, within its first 15 lines and in its language's comment syntax, with:

```
# effect: read-only        (or: effect: writes)
# cost: heavy              (optional)
```

`read-only` means it writes nothing outside `artifacts/`, mutates no external system, changes no git state and installs nothing: it prints its result and the skill captures it. Anything else is `writes`. `cost: heavy` marks a read that could overload what it reads.

Before running a script, verify its header against its code:

```
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" effect {script} [--context {namespace}/{product}]
```

The report holds `declared_effect`, `cost`, `reasons` and `run_without_asking`. When it is `true`, run the script. Otherwise `reasons` says why: a `writes` declaration, a header that is absent or that the code contradicts, `cost: heavy`, or a target the effective config lists under `sensitive`. Then show what the script does, what it reads and where its output lands, and wait for the user's approval of that run. The approval covers that run, not the script forever, and a plan step authorizing the work does not authorize running a script the step produces.

Never run anything that writes to an external system, approved or not.
