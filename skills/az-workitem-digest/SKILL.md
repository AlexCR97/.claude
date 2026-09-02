---
name: az-workitem-digest
description: Reads an Azure DevOps work item by ID (user story, bug, or task), analyzes its description, acceptance criteria, attached files and images, and related work items, then outputs a structured digest.
---

## Input

The user must supply a **work item ID**. It may be passed as an argument to the skill invocation (e.g. `/az-workitem-digest 12345`) or stated in the message. If no ID is provided, ask the user for one before proceeding.

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

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Read the config

Read credentials from:

```
~/.az-workitems/config.json
```

If the file does not exist, stop and tell the user:

> No config found. Run `/az-workitem-init` first to set up your Azure DevOps connection.

### 2. Check for raw data

Check that the fetch output exists:

```
~/.az-workitems/{id}/raw/raw.json
```

If it does not exist, stop and tell the user:

> No raw data found for work item #{id}. Run `/az-workitem-fetch {id}` first.

### 3. Analyze the raw data and assets

Read `~/.az-workitems/{id}/raw/raw.json`. The structure is:

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
        "source": "relation" | "comment_inline_image" | "field_inline:{field}",
        "url": "{ado-url}",
        "comment_id": {id} | null,
        "name": "{original filename}",           ← display name, may collide
        "local_filename": "{guid}.{ext}" | null, ← on-disk name; null if download failed
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

#### 3a. Work item fields

From `tree.work_item.fields`, extract:

| Field                     | JSON key                                                |
| ------------------------- | ------------------------------------------------------- |
| ID                        | `System.Id`                                             |
| Type                      | `System.WorkItemType`                                   |
| Title                     | `System.Title`                                          |
| Area                      | `System.AreaPath`                                       |
| Sprint                    | `System.IterationPath`                                  |
| Description / Repro Steps | `System.Description` or `Microsoft.VSTS.TCM.ReproSteps` |
| Acceptance Criteria       | `Microsoft.VSTS.Common.AcceptanceCriteria`              |
| Assigned To               | `System.AssignedTo.displayName`                         |
| Tags                      | `System.Tags`                                           |

Description and Acceptance Criteria fields contain HTML. Strip all tags to get the plain text, then synthesize — do not copy verbatim into the digest (see the digest template for the expected format of each section).

#### 3b. Discussion

From `tree.discussion.comments`, sort by `createdDate` ascending. For each comment, parse the `text` field (HTML) to extract:

1. **Plain text** — strip all HTML tags
2. **@mentions** — `<a data-vss-mention>` elements; extract the visible display name
3. **Work item references** — `<a href=".../_workitems/edit/{id}/">` or `#{number}` text patterns; note the referenced IDs and cross-reference them against the `tree.related` data already fetched

#### 3c. Attachments and inline images

For each entry in `tree.attachments` where `download_ok` is `true`, the file is available at:

```
~/.az-workitems/{id}/raw/{local_filename}
```

Attachment files on disk are named after their ADO attachment GUID (plus the
original extension), because ADO names every pasted screenshot `image.png`.
Always use `local_filename` for the path and `name` for any text shown to the
reader — never assume the two match.

Read and analyze each file:

- **Image files** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`) — view visually and describe what is shown (error screenshot, UI mockup, diagram, log output, etc.). Note where the image came from: the comment id if `source` is `comment_inline_image`, or the field it is embedded in if `source` starts with `field_inline:` (e.g. `field_inline:System.Description`).
- **Other files** (`.pdf`, `.docx`, `.txt`, `.md`, `.csv`, etc.) — read the content and summarize the relevant information.

If `download_ok` is `false` for an attachment, note it as unavailable in the digest.

#### 3d. Related work items

Walk `tree.related` recursively. For each node that was not skipped, extract its title, type, and state from `node.work_item.fields`. Group by `relation_type` (parent / child / related).

Nodes with a `skipped_reason` of `already_visited` or `max_depth_reached` should be listed as references only (ID, no title).

### 4. Write the digest

Write the digest to:

```
~/.az-workitems/{id}/digest.md
```

Do not print the full digest body in chat. Once the file is written, confirm with a single line:

> Digest written to `~/.az-workitems/{id}/digest.md`

#### Link patterns

Use these URL patterns wherever references appear in the digest:

| Reference type | Pattern                                                                             |
| -------------- | ----------------------------------------------------------------------------------- |
| Work item      | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`                        |
| Comment        | `https://dev.azure.com/{org}/{project}/_workitems/edit/{work-item-id}#{comment-id}` |
| Attachment     | the local file when downloaded; otherwise the original `url` from `raw.json`        |

For attachments, **always prefer the local downloaded file over the remote URL**. When an attachment has `download_ok: true`, link to the local copy using a path relative to the digest (`digest.md` lives in `~/.az-workitems/{id}/`, so the file is at `raw/{local_filename}`). Only fall back to the original remote `url` when `download_ok` is `false` (i.e. no local file is present).

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
