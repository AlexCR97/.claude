---
name: ticket-init
description: Initializes the ~/.tickets directory and the connection for one ticket source. Run this once per machine per source before using any other ticket-* skill — new, fetch, refine, digest, plan, implement, checkpoint, or resume. Also migrates data from the older az-workitem layout.
argument-hint: "[source] [provider options]"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory | Contains | Read |
| --- | --- | --- |
| `ticket-common/` | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md` | as each step names |
| `ticket-providers/{source}/` | everything specific to where the ticket came from | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md` | everything specific to what shape the work is | not read by this skill |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

No `allowed-tools` here: this skill writes config and runs a migration, so an allowlist narrow enough to be meaningful would also block the work.

---

## Purpose

Sets up one ticket source for the current user: resolves which source, acquires and validates whatever credential it needs, and writes its config. Also records the machine's `default_source`, so a bare id resolves without a prefix.

The config lives in the user's home directory, so it is shared across every workspace. The other `ticket-*` skills read it automatically.

Run it once per machine per source. Running it again for a source that is already set up is a re-initialization, and it asks first.

**Read `ticket-providers/{source}/config.md`** for what that source stores, what defaults it applies, how its credential is acquired, and how it is validated. This file deliberately holds none of that: there is no default organization here, no credential command, and no coordinate flag.

---

## Input

```
/ticket-init [{source}] [{provider options}]
```

- `{source}` — which source to set up. When omitted, see step 2.
- `{provider options}` — anything that source's `config.md` documents. **Pass through only what the user explicitly supplied**; every omitted flag keeps that source's own default.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Enumerate the installed sources

```bash
python "{skills}/ticket-common/ticket.py" sources
```

This is the list of what can be initialized. **Never assume a fixed set**, and never assume a particular source is the one meant — sources are discovered by glob, and the set changes when a directory is added.

The output also carries the current `default_source` and each source's capabilities, which is what step 5 reports.

### 2. Resolve which source

Take the source the user supplied. If they supplied none:

- Where exactly one source is installed, use it and say so.
- Where more than one is, list them with their `kind` and capabilities and **ask**. Do not pick one, and in particular do not treat whichever is alphabetically first or historically usual as the answer.

### 3. Check for an existing config

```bash
python "{skills}/ticket-common/ticket.py" resolve --source {source}
```

The `config` it returns is the stored config with any credential replaced by its **status string** — never the credential itself. If `on_disk.config` is true, show those values and ask `Re-initialize? [y/N]`. If the user declines, stop here — do not proceed to step 4.

### 4. Run the migration check

**Every invocation, regardless of which source was chosen.** Data from the older layout is migrated by a script, because renaming directories and rewriting config are the two operations where a half-completed pass is worst, and neither requires any judgement.

Dry-run it first:

```bash
python "{skills}/ticket-common/ticket.py" migrate --dry-run
```

- `result` is `nothing_to_migrate` → say nothing and continue to step 5.
- Otherwise → **show the report and ask** before running it for real. Name how many tickets would be copied and where they would land.

On approval, run the same verb without `--dry-run` and report what it did.

The script **copies; it does not move**. `journal.md` is the one file in this system that nothing can regenerate, so a copy is a free backup of the irreplaceable thing. Say that the old tree was left intact and can be deleted whenever the user chooses.

It never merges into an existing destination and never overwrites an existing config — either is reported as skipped. Do not work around a skip by hand: a partial merge of two plan histories is unrecoverable.

### 5. Run the init

```bash
python "{skills}/ticket-common/ticket.py" init --source {source} [{provider options}]
```

**Read `ticket-providers/{source}/config.md` first** — it is the only source of that source's defaults, its credential command, its validation call, and what each failure status means. Pass a provider option only for a value the user explicitly supplied.

Never ask the user for a credential, and never run a credential command yourself. Credential handling belongs to the provider module, which is why this skill has no way to see one.

Wait for the script to complete. If it exits with a non-zero code, report the error output verbatim and stop — do not write or modify any file yourself.

### 6. Report the result

On success:

> `{source}` initialized. Config written to `{source config path}`.
> You can now run `/ticket-fetch {source}:{id}` to pull a ticket down.

Also state:

- **Which values were used, and which came from a default** — so a default is never applied silently. That list is in the init's own output.
- **Whether `default_source` was set**, and to what. The front door sets it only when no default existed; an init for a second source **never silently repoints it**. Where a default already existed, say which source it is and that bare ids still resolve there.
- Anything the source's `config.md` says is worth reporting — a credential's expiry, how it refreshes, what the user must keep doing to stay signed in.

Where the source offers `new` rather than `fetch`, point at `/ticket-new` instead; the capabilities in step 1's output say which.

On failure, report the error output from the script verbatim and stop.

---

## Constraints

- Never write or modify a config file directly — always delegate to the front door
- Never print a credential value in chat, and never paste one into a command
- Never ask the user for a credential of any kind — the provider acquires and refreshes it
- Never run a credential command yourself — that belongs to the provider module
- Never pass a provider option unless the user supplied that value — let the source apply its own defaults
- Never assume which sources exist; enumerate them
- Never silently repoint `default_source` — report what it is, and change it only when there was none
- Run the migration check on every invocation, and never run the migration for real without showing the dry run and asking
- Do not proceed past a non-zero exit code
