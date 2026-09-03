---
name: az-workitem-init
description: Initializes the ~/.az-workitems directory and config.json in the user's home directory. Run this once per machine before using az-workitem-fetch, az-workitem-refine, az-workitem-digest, az-workitem-plan, or az-workitem-implement.
---

## Purpose

Sets up the Azure DevOps connection for the current user by resolving the organization and project, acquiring an Azure DevOps access token through the Azure CLI, validating it against ADO, and writing all three to `~/.az-workitems/config.json`.

Both values have defaults, so in the common case this skill needs no input at all:

| Value        | Default      |
| ------------ | ------------ |
| Organization | `edwire`     |
| Project      | `EW.Educate` |

Override a default **only** when the user explicitly supplies that value.

### How authentication works

There is no PAT. Credentials come from the Azure CLI, and the user is never asked for one — they only need to stay signed in with `az login`:

```bash
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798
```

The **entire JSON response** is stored under the `token` key in `config.json`:

```json
{
  "organization": "edwire",
  "project": "EW.Educate",
  "token": {
    "accessToken": "eyJ0eXAiOiJKV1Qi…",
    "expiresOn": "2026-09-03 17:48:31.000000",
    "expires_on": 1788479311,
    "subscription": "…",
    "tenant": "…",
    "tokenType": "Bearer"
  }
}
```

Every `az-workitem-*` script reuses that cached token while it is still good, and re-runs the Azure CLI to replace it once it is within five minutes of expiring — writing the fresh response back to `config.json`. Tokens live about an hour, so the refresh is routine and needs no user involvement. `tokenType` and `accessToken` form the `Authorization` header.

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

- Exit code **0** → config exists. The script prints the current values, with the token reduced to its status. Show them to the user and ask `Overwrite? [y/N]`. If the user declines, stop here — do not proceed to step 2.
- Exit code **1** → config not found (`not_found` is printed). Proceed to step 2.

### 2. Resolve the organization and project

Take the values the user supplied with the skill invocation (e.g. `/az-workitem-init mycompany MyProject`):

- **Organization** — the ADO org name (e.g. `mycompany`, not the full URL)
- **Project** — the ADO project name (e.g. `MyProject`)

Do **not** ask for either value when the user did not supply it — the script fills them in from the defaults above.

Never ask for a PAT or any other credential. The script acquires the token itself.

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
  --project "{project}"
```

There is no credential flag. The script will:

- Default `--org` to `edwire` and `--project` to `EW.Educate`
- Acquire a fresh Azure DevOps token with `az account get-access-token`
- Validate it against ADO (`GET /_{org}/_apis/projects/{project}`)
- On success: create `~/.az-workitems/` and write `config.json`, with the whole token response under `token`
- On failure: exit with a non-zero code and print an error message

The script never prompts — a missing Azure CLI or an expired `az login` surfaces as a clear error instead of a hang.

Wait for the script to complete before continuing.

### 4. Report the result

**If the script exits with code 0:**

> Workspace initialized. Config written to `~/.az-workitems/config.json`.
> You can now run `/az-workitem-digest {id}` to fetch a work item.

Also state which organization and project were used, so a default is never applied silently, and when the token expires. Add that the token refreshes itself on later runs, as long as the user stays signed in with `az login`.

**If the script exits with a non-zero code:**

Report the error output from the script verbatim and stop. Do not write or modify any files yourself.

---

## Constraints

- Never write or modify `config.json` directly — always delegate to the script
- Never print the `accessToken` value in chat, and never paste it into a command
- Never pass `--org` or `--project` unless the user supplied that value — let the script apply its defaults
- Never ask the user for a PAT, a token, or any other credential — the script acquires and refreshes it
- Never run `az account get-access-token` yourself — token handling belongs to the scripts
- Do not proceed past step 3 if the script exits with a non-zero code
