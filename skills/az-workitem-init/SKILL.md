---
name: az-workitem-init
description: Initializes the .claude/.az-workitems directory and config.json for the current workspace. Run this once before using az-workitem-fetch, az-workitem-refine, az-workitem-digest, az-workitem-plan, or az-workitem-implement.
---

## Purpose

Sets up the Azure DevOps connection for the current workspace by collecting the organization name, project name, and a Personal Access Token (PAT), validating them against ADO, and writing them to `.claude/.az-workitems/config.json`.

Run this skill once per workspace. The other `az-workitem-*` skills read this config automatically.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Check for existing config

Locate the check script relative to this skill file:

```
skills/az-workitem-init/check-az-config.py
```

Run it from the **current working directory of the session**:

```bash
python "{path-to-skill}/check-az-config.py"
```

- Exit code **0** → config exists. The script prints the current values (PAT masked). Show them to the user and ask `Overwrite? [y/N]`. If the user declines, stop here — do not proceed to step 2.
- Exit code **1** → config not found (`not_found` is printed). Proceed to step 2.

### 2. Collect credentials

Ask the user for the following values if they have not already been provided:

- **Organization** — the ADO org name (e.g. `mycompany`, not the full URL)
- **Project** — the ADO project name (e.g. `MyProject`)
- **PAT** — a Personal Access Token with at least `Work Items (Read)` scope

If the user passes any of these as arguments to the skill invocation (e.g. `/az-workitem-init mycompany MyProject`), use those values and only prompt for whatever is missing.

Do not proceed until all three values are in hand.

### 3. Run the init script

Locate the script relative to this skill file:

```
skills/az-workitem-init/init-az-workitems.py
```

Run it from the **current working directory of the session**, passing all three values as CLI arguments:

```bash
python "{path-to-skill}/init-az-workitems.py" \
  --org {org} \
  --project "{project}" \
  --pat {PAT}
```

The script will:

- Prompt interactively for any value not supplied via CLI args
- Validate the credentials against ADO (`GET /_{org}/_apis/projects/{project}`)
- On success: create `.claude/.az-workitems/` and write `config.json`
- On failure: exit with a non-zero code and print an error message

Wait for the script to complete before continuing.

### 4. Report the result

**If the script exits with code 0:**

> Workspace initialized. Config written to `.claude/.az-workitems/config.json`.
> You can now run `/az-workitem-digest {id}` to fetch a work item.

**If the script exits with a non-zero code:**

Report the error output from the script verbatim and stop. Do not write or modify any files yourself.

---

## Constraints

- Never write or modify `config.json` directly — always delegate to the script
- Never print the raw PAT value in chat
- Do not proceed past step 3 if the script exits with a non-zero code
