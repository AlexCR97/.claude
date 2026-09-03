---
name: az-workitem-fetch
description: Fetches raw Azure DevOps work item data (fields, comments, attachments, related items) and writes it to ~/.az-workitems/{id}/raw/. Always re-fetches raw.json; keeps existing attachment files and only downloads new ones. Required before running az-workitem-refine or az-workitem-digest.
---

## Purpose

Downloads everything the ADO API knows about a work item and stores it locally so that `az-workitem-refine` and `az-workitem-digest` can work offline from a consistent snapshot. Run this skill any time you want to refresh the data.

**Recommended skill order:**

```
az-workitem-init → az-workitem-fetch → az-workitem-refine → [fetch → refine → …] → az-workitem-digest → az-workitem-plan → az-workitem-implement
```

---

## Paths

All `az-workitem-*` data lives under the current user's home directory, so the
paths below are the same no matter which workspace the session runs in:

```
~/.az-workitems/
```

`~` is written for brevity. Neither the file tools nor a quoted shell argument
expand it, so **resolve it to an absolute path before use** — `C:\Users\{user}`
on Windows, `/home/{user}` on Linux, `/Users/{user}` on macOS.

---

## Input

The user must supply a **work item ID**. It may be passed as an argument (e.g. `/az-workitem-fetch 12345`) or stated in the message. If no ID is provided, ask for one before proceeding.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Verify prerequisites

Check that Python 3 is available:

```bash
python --version
```

If Python is not installed, inform the user and stop.

### 2. Read the config

Read the organization and project from:

```
~/.az-workitems/config.json
```

If the file does not exist, stop and tell the user:

> No config found. Run `/az-workitem-init` first to set up your Azure DevOps connection.

### 3. Run the fetch script

Locate the script relative to this skill file:

```
skills/az-workitem-fetch/fetch-work-item.py
```

The script resolves its own output location under the user's home directory, so it can be run from anywhere:

```bash
python "{path-to-skill}/fetch-work-item.py" --id {work-item-id} --org {org} --project "{project}"
```

There is no credential flag — never pass one, and never read the token out of `config.json` yourself. The script uses the cached token and refreshes it through the Azure CLI when it is close to expiring.

The script will:

- Always re-download `raw.json` with fresh data from ADO
- Abort with a non-zero exit code if ADO returns 401 mid-fetch, rather than writing a partially downloaded `raw/`
- Keep attachment files already present on disk from a previous fetch
- Download only attachments that are new or missing
- Write everything to:

```
~/.az-workitems/{id}/raw/raw.json     ← all API data (always refreshed)
~/.az-workitems/{id}/raw/{filename}   ← attachment files
```

Wait for the script to complete. If it exits with an error, report the stderr output to the user and stop.

### 4. Confirm

Report the result with a single line:

> Fetched work item #{id} — raw data written to `~/.az-workitems/{id}/raw/`.

---

## Constraints

- Never modify the work item in ADO
- Never delete existing attachment files — the script skips files already on disk
- Do not proceed past step 3 if the script exits with a non-zero code
