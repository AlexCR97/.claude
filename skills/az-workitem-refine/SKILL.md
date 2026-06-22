---
name: az-workitem-refine
description: Runs an interactive refinement session between Claude and the user to challenge and sharpen a work item's requirements against the existing codebase, domain model, and business context. Posts a structured Q&A summary as a comment on the ADO work item when complete.
---

## Purpose

Raw work items often under-specify what "done" looks like. This skill reads the fetched work item data and conducts a structured interview — covering goal and success criteria, domain model and data, and edge cases and failure modes — to surface ambiguities and resolve them before any planning or implementation begins. The agreed refinements are posted back to ADO as a discussion comment.

**Recommended skill order:**

```
az-workitem-init → az-workitem-fetch → az-workitem-refine → [fetch → refine → …] → az-workitem-digest → az-workitem-plan → az-workitem-implement
```

You may run `az-workitem-fetch` followed by `az-workitem-refine` multiple times in a loop as the work item evolves and the ADO comment history grows.

---

## Input

The user must supply a **work item ID**. It may be passed as an argument (e.g. `/az-workitem-refine 12345`) or stated in the message. If no ID is provided, ask for one before proceeding.

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

### 3. Check for raw data

Check that the fetch output exists:

```
.claude/.az-workitems/{id}/raw/raw.json
```

If it does not exist, stop and tell the user:

> No raw data found for work item #{id}. Run `/az-workitem-fetch {id}` first.

### 4. Load the work item context

Read `.claude/.az-workitems/{id}/raw/raw.json` and extract the following from `tree.work_item.fields`:

- **Title** (`System.Title`)
- **Type** (`System.WorkItemType`)
- **State** (`System.State`)
- **Description / Repro Steps** (`System.Description` or
  `Microsoft.VSTS.TCM.ReproSteps`) — strip HTML to plain text
- **Acceptance Criteria** (`Microsoft.VSTS.Common.AcceptanceCriteria`) — strip HTML to plain text

Also read:

- **Discussion** — `tree.discussion.comments`, sorted by `createdDate` ascending, stripped of HTML
- **Attachments** — for each entry in `tree.attachments` where `download_ok` is `true`, read and internalize the file so you can reference it during the interview
- **Related work items** — titles and types from `tree.related`, for domain context

This combined context is the foundation for challenging the user's requirements.

### 5. Conduct the refinement interview

Run a structured interview in **three rounds**. In each round, present all questions for that domain together, wait for the user's answers, then move to the next round. If any answer raises a follow-up question, ask it before advancing to the next round.

#### Question format

Present each question in this format:

```
{N.M} {Question}

> Recommended: {your recommended answer, derived from the work item context and codebase}
```

Where `N` is the round number and `M` is the question number within the round.

Example:

```
1.1 What is the single most important outcome this work item must deliver?

> Recommended: Based on the acceptance criteria, the primary outcome is that a user can export their invoice history as a CSV file from the account portal.
```

After presenting all questions in a round, wait for the user's response before continuing. Accept partial answers — the user may skip questions they consider already clear, or override your recommendation.

#### Round 1 — Goal and success criteria

Cover:

- What is the single most important outcome this work item must deliver?
- What does "done" look like from the end user's perspective?
- Are the acceptance criteria complete, or are there implicit expectations not captured?
- What would signal that this feature or fix has failed in production?

#### Round 2 — Domain model and data

Cover:

- Which services and projects are involved in or affected by this work item? (e.g. files, folders, directories, backends, frontends, APIs, databases, shared libraries)
- Which domain entities are created, updated, deleted or involved in any way by this work item?
- Are there any new fields, relationships, or constraints being introduced to the data model?
- What invariants must always hold after this change? (e.g. uniqueness, foreign key integrity, business rules)
- Are there existing patterns in the codebase this should follow? If so, which files or classes are the best reference?
- Does this change affect any shared contracts (APIs, events, DTOs, database schemas) that other services depend on?

#### Round 3 — Edge cases and failure modes

Cover:

- What happens if the input is invalid, missing, or malformed?
- What happens under concurrent access — can two users trigger conflicting operations simultaneously?
- What is the expected behavior if a downstream dependency (database, external API, message broker) is unavailable?
- Are there any rollback or compensating actions needed if this operation fails midway?
- Are there any security or authorization edge cases — users accessing data they should not, or privilege escalation paths?

#### Follow-up rounds

If any answer in rounds 1–3 surfaces a new ambiguity or dependency, open a follow-up round before closing the interview. Repeat until no open questions remain.

### 6. Synthesize the refinement summary

Once the interview is complete, compile a structured summary using the template at `skills/az-workitem-refine/refinement-template.html`. This will become the ADO comment.

Rules:

- The template is HTML — produce valid HTML, not markdown
- Replace every `{placeholder}` with the actual value derived from the interview
- Omit the Open Items section (`<h2>` and its content) if everything was resolved

### 7. Show the preview and confirm

Print the full summary in chat and ask:

> Does this look correct? Reply "yes" to post it to ADO, or tell me what to change.

Wait for the user's response. If they request changes, update the summary and show the revised version. Repeat until they confirm.

### 8. Write the comment file

Write the confirmed summary to a temporary file:

```
.claude/.az-workitems/{id}/refinement-comment.html
```

### 9. Post the comment to ADO

Locate the script relative to this skill file:

```
skills/az-workitem-refine/post-refinement-comment.py
```

Run it:

```bash
python "{path-to-skill}/post-refinement-comment.py" --id {work-item-id} --org {org} --project "{project}" --pat {PAT} --comment-file ".claude/.az-workitems/{id}/refinement-comment.html" --delete-after-post
```

Wait for the script to complete. If it exits with an error, report the stderr output and stop — do not retry automatically.

### 10. Confirm

Report the result with a single line:

> Refinement comment posted to work item #{id}.
> Run `/az-workitem-fetch {id}` to pull the updated discussion, then
> `/az-workitem-digest {id}` when you are ready to generate the digest.

---

## Constraints

- Never modify source code files
- Never run git operations
- Never post the comment without the user's explicit confirmation in step 7
- Do not fabricate codebase patterns — only reference files and classes that actually exist
- Never print the raw PAT value in chat
- Do not delete `refinement-comment.md` manually — the script deletes it automatically via `--delete-after-post` once the comment is confirmed posted
