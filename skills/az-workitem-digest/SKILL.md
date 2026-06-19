---
name: az-workitem-digest
description: Reads an Azure DevOps work item by ID (user story, bug, or task), analyzes its description, acceptance criteria, attached files and images, and related work items, then outputs a structured digest and high-level implementation steps.
---

## Input

The user must supply a **work item ID**. It may be passed as an argument to the skill invocation (e.g. `/az-workitem-digest 12345`) or stated in the message. If no ID is provided, ask the user for one before proceeding.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Verify prerequisites

Check that Python 3 is available:

```bash
python --version
```

If Python is not installed, inform the user and stop.

### 2. Resolve organization, project, and credentials

Locate the `.claude` directory for the current working directory of the session:

- If a `.claude` directory exists in the current working directory, use it.
- Otherwise, create `.claude` in the current working directory.

Check for an existing config file at:

```
{cwd}/.claude/.az-workitems/config.json
```

If it exists, read the values from it:

```json
{
  "organization": "{org}",
  "project": "{project}",
  "pat": "{PAT}"
}
```

If the file does not exist, or any of the three values is missing from it, ask the user to provide the missing values:

- **Organization** — the ADO org name (e.g. `mycompany`, not the full URL)
- **Project** — the ADO project name (e.g. `MyProject`)
- **PAT** — a Personal Access Token with at least `Work Items (Read)` scope

Once all three values are available, write (or overwrite) the config file with the resolved values before proceeding:

```bash
mkdir -p {cwd}/.claude/.az-workitems
```

```json
{
  "organization": "{org}",
  "project": "{project}",
  "pat": "{PAT}"
}
```

Use this same `{cwd}/.claude` root for all output paths in subsequent steps.

Do not proceed until all three values are available.

### 3. Run the data-fetching script

Locate the script relative to this skill file:

```
skills/az-workitem-digest/digest-work-item.py
```

Run it from the **current working directory of the session**:

```bash
python "{path-to-skill}/digest-work-item.py" \
  --id {work-item-id} \
  --org {org} \
  --project "{project}" \
  --pat {PAT}
```

The script will:

- Fetch the work item, its comments, and all related work items (parent / children / related) recursively up to 3 levels deep
- Download all attachments — both from `relations` and inline images embedded in comment HTML
- Write everything to:

```
.claude/.az-workitems/{id}/raw/raw.json     ← all API data
.claude/.az-workitems/{id}/raw/{filename}   ← downloaded files
```

Wait for the script to complete before proceeding. If it exits with an error, report the stderr output to the user and stop.

### 4. Analyze the raw data and assets

Read `.claude/.az-workitems/{id}/raw/raw.json`. The structure is:

```
{
  "meta": {
    "organization": "{org}",
    "project": "{project}",
    "work_item_id": {id},
    ...
  },
  "tree": {
    "id": {id},
    "work_item": { ... },       ← full ADO work item response
    "discussion": {             ← comments API response
      "comments": [ ... ]
    },
    "attachments": [            ← all attachments for this node
      {
        "source": "relation" | "comment_inline_image",
        "name": "{filename}",
        "url": "{ado-url}",
        "comment_id": {id} | null,
        "local_filename": "{filename}" | null,   ← null if download failed
        "download_ok": true | false
      }
    ],
    "related": [                ← recursively resolved related work items
      {
        "relation_type": "parent" | "child" | "related",
        ... (same structure as tree node, or { id, skipped_reason } if skipped)
      }
    ]
  }
}
```

#### 4a. Work item fields

From `tree.work_item.fields`, extract:

| Field                     | JSON key                                                |
| ------------------------- | ------------------------------------------------------- |
| ID                        | `System.Id`                                             |
| Type                      | `System.WorkItemType`                                   |
| Title                     | `System.Title`                                          |
| State                     | `System.State`                                          |
| Description / Repro Steps | `System.Description` or `Microsoft.VSTS.TCM.ReproSteps` |
| Acceptance Criteria       | `Microsoft.VSTS.Common.AcceptanceCriteria`              |
| Priority                  | `Microsoft.VSTS.Common.Priority`                        |
| Assigned To               | `System.AssignedTo.displayName`                         |
| Tags                      | `System.Tags`                                           |

Description and Acceptance Criteria fields contain HTML. Strip all tags to get the plain text, then synthesize — do not copy verbatim into the digest (see the digest template for the expected format of each section).

#### 4b. Discussion

From `tree.discussion.comments`, sort by `createdDate` ascending. For each comment, parse the `text` field (HTML) to extract:

1. **Plain text** — strip all HTML tags
2. **@mentions** — `<a data-vss-mention>` elements; extract the visible display name
3. **Work item references** — `<a href=".../_workitems/edit/{id}/">` or `#{number}` text patterns; note the referenced IDs and cross-reference them against the `tree.related` data already fetched

#### 4c. Attachments and inline images

For each entry in `tree.attachments` where `download_ok` is `true`, the file is available at:

```
.claude/.az-workitems/{id}/raw/{local_filename}
```

Read and analyze each file:

- **Image files** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`) — view visually and describe what is shown (error screenshot, UI mockup, diagram, log output, etc.). Note which comment the image came from if `source` is `comment_inline_image`.
- **Other files** (`.pdf`, `.docx`, `.txt`, `.md`, `.csv`, etc.) — read the content and summarize the relevant information.

If `download_ok` is `false` for an attachment, note it as unavailable in the digest.

#### 4d. Related work items

Walk `tree.related` recursively. For each node that was not skipped, extract its title, type, and state from `node.work_item.fields`. Group by `relation_type` (parent / child / related).

Nodes with a `skipped_reason` of `already_visited` or `max_depth_reached` should be listed as references only (ID, no title).

### 5. Write the digest

Write the digest to:

```
.claude/.az-workitems/{id}/digest.md
```

Do not print the full digest body in chat. Once the file is written, confirm with a single line:

> Digest written to `.claude/.az-workitems/{id}/digest.md`

#### Link patterns

Use these URL patterns wherever references appear in the digest:

| Reference type | Pattern                                                                                          |
| -------------- | ------------------------------------------------------------------------------------------------ |
| Work item      | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`                                     |
| Comment        | `https://dev.azure.com/{org}/{project}/_workitems/edit/{work-item-id}?discussionId={comment-id}` |
| Attachment     | the original `url` from `raw.json`                                                               |

#### Digest template

Read the template from `skills/az-workitem-digest/digest-template.md` and use it as the structure for the output file.

Rules:

- Omit any section that has no content
- Replace every `{placeholder}` with the actual value derived from the raw data and analysis

---

## Constraints

- Never modify, update, or close the work item
- Derive all content strictly from `raw.json` and the downloaded assets — do not fabricate
- Strip all HTML from description, acceptance criteria, and comment text before writing to the digest
- If a related work item was skipped due to `max_depth_reached` or `already_visited`, list it by ID only
- If an attachment download failed, note it as unavailable rather than omitting it silently
- The Implementation Steps must be specific to this work item, not a generic template
