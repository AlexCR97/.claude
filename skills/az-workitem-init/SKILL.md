---
name: az-workitem-init
description: Initializes the ~/.az-workitems directory and config.json in the user's home directory. Run this once per machine before using az-workitem-fetch, az-workitem-refine, az-workitem-digest, az-workitem-plan, or az-workitem-implement.
---

## Purpose

Sets up the Azure DevOps connection for the current user by resolving the organization name, project name, and a Personal Access Token (PAT), validating them against ADO, and writing them to `~/.az-workitems/config.json`.

All three values have defaults, so in the common case this skill needs no input at all:

| Value        | Default                                                                                                        |
| ------------ | -------------------------------------------------------------------------------------------------------------- |
| Organization | `edwire`                                                                                                         |
| Project      | `EW.Educate`                                                                                                     |
| PAT          | `az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken --output tsv`    |

Override a default **only** when the user explicitly supplies that value.

Run this skill once per machine. The config lives in the user's home directory (`~`, i.e. `C:\Users\{user}` on Windows and `/home/{user}` or `/Users/{user}` on Linux/macOS), so it is shared across every workspace. The other `az-workitem-*` skills read it automatically.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Check for existing config

Locate the check script relative to this skill file:

```
skills/az-workitem-init/check-az-config.py
```

The script resolves the config path under the user's home directory, so it can be run from anywhere:

```bash
python "{path-to-skill}/check-az-config.py"
```

- Exit code **0** → config exists. The script prints the current values (PAT masked). Show them to the user and ask `Overwrite? [y/N]`. If the user declines, stop here — do not proceed to step 2.
- Exit code **1** → config not found (`not_found` is printed). Proceed to step 2.

### 2. Resolve credentials

Take only the values the user supplied with the skill invocation (e.g. `/az-workitem-init mycompany MyProject`):

- **Organization** — the ADO org name (e.g. `mycompany`, not the full URL)
- **Project** — the ADO project name (e.g. `MyProject`)
- **PAT** — a Personal Access Token with at least `Work Items (Read)` scope

Do **not** ask the user for a value they did not supply — the script fills each one in from the defaults above. In particular, never ask for a PAT: the script acquires an Azure DevOps access token through the Azure CLI, which only requires the user to be signed in via `az login`.

### 3. Run the init script

Locate the script relative to this skill file:

```
skills/az-workitem-init/init-az-workitems.py
```

Run it with **no arguments** to accept every default — it resolves its own output location under the user's home directory:

```bash
python "{path-to-skill}/init-az-workitems.py"
```

Pass a flag only for a value the user explicitly supplied; every omitted flag keeps its default:

```bash
python "{path-to-skill}/init-az-workitems.py" \
  --org {org} \
  --project "{project}" \
  --pat {PAT}
```

The script will:

- Default `--org` to `edwire` and `--project` to `EW.Educate`
- Default `--pat` to an Azure DevOps access token from `az account get-access-token`
- Validate the credentials against ADO (`GET /_{org}/_apis/projects/{project}`)
- On success: create `~/.az-workitems/` and write `config.json`
- On failure: exit with a non-zero code and print an error message

The script never prompts — a missing Azure CLI or an expired `az login` surfaces as a clear error instead of a hang.

Wait for the script to complete before continuing.

### 4. Report the result

**If the script exits with code 0:**

> Workspace initialized. Config written to `~/.az-workitems/config.json`.
> You can now run `/az-workitem-digest {id}` to fetch a work item.

Also state which organization and project were used, so a default is never applied silently. When the PAT came from the Azure CLI, add that such access tokens expire after about an hour — re-run this skill when another `az-workitem-*` skill reports an authentication failure.

**If the script exits with a non-zero code:**

Report the error output from the script verbatim and stop. Do not write or modify any files yourself.

---

## Constraints

- Never write or modify `config.json` directly — always delegate to the script
- Never print the raw PAT value in chat
- Never pass `--org`, `--project`, or `--pat` unless the user supplied that value — let the script apply its defaults
- Never ask the user for a value that has a default
- Do not proceed past step 3 if the script exits with a non-zero code
