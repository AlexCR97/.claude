---
name: az-workitem-fetch
description: Fetches raw Azure DevOps work item data (fields, comments, attachments, related items) and writes it to .claude/.az-workitems/{id}/raw/. Always re-fetches raw.json; keeps existing attachment files and only downloads new ones. Required before running az-workitem-refine or az-workitem-digest.
---

## Purpose

Downloads everything the ADO API knows about a work item and stores it locally so that `az-workitem-refine` and `az-workitem-digest` can work offline from a consistent snapshot. Run this skill any time you want to refresh the data.

**Recommended skill order:**

```
az-workitem-init → az-workitem-fetch → az-workitem-refine → [fetch → refine → …] → az-workitem-digest → az-workitem-plan → az-workitem-implement
```

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

Read credentials from:

```
.claude/.az-workitems/config.json
```

If the file does not exist, stop and tell the user:

> No config found. Run `/az-workitem-init` first to set up your workspace.

### 3. Run the fetch script

Locate the script relative to this skill file:

```
skills/az-workitem-fetch/fetch-work-item.py
```

Run it from the **current working directory of the session**:

```bash
python "{path-to-skill}/fetch-work-item.py" --id {work-item-id} --org {org} --project "{project}" --pat {PAT}
```

The script will:

- Always re-download `raw.json` with fresh data from ADO
- Keep attachment files already present on disk from a previous fetch
- Download only attachments that are new or missing
- Write everything to:

```
.claude/.az-workitems/{id}/raw/raw.json     ← all API data (always refreshed)
.claude/.az-workitems/{id}/raw/{filename}   ← attachment files
```

Wait for the script to complete. If it exits with an error, report the stderr output to the user and stop.

### 4. Confirm

Report the result with a single line:

> Fetched work item #{id} — raw data written to `.claude/.az-workitems/{id}/raw/`.

---

## Constraints

- Never modify the work item in ADO
- Never delete existing attachment files — the script skips files already on disk
- Do not proceed past step 3 if the script exits with a non-zero code
