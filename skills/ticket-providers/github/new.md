# github — new

Read by `ticket-create`. Creating an issue writes to GitHub, so it is **gated behind an explicit confirmation**: the ticket outlives the session and is visible to everyone who can see the repository.

## The flow

1. **Propose.** Nothing is written.

   ```
   python "{skills}/ticket-common/ticket.py" new --source github --title "…" --type {type} [--body-file F] [--criteria-file F] [--label L ...] --propose [--in {namespace}/{product}]
   ```

   It reports the product it would be filed under and a `proposal`: the repository, title, type, the `labels` that will be applied, and the full `body`. Show **all** of it — the product, title, type, body and labels — and let the user correct any of it. Re-run `--propose` for each correction.

2. **Ask.** Require an explicit yes. A vague answer is not a yes. Without `--confirm` the front door refuses to write, exiting 4.

3. **Create.** Re-run the same command with `--confirm` instead of `--propose`. It creates the issue, **fetches it immediately**, and files it under the number GitHub assigned, so it behaves like any other fetched ticket. The report carries `created` (with the number and URL), `fetched` and the resulting `ticket_json`.

## What is sent

| Field | How it is supplied |
| --- | --- |
| Title | `--title` |
| Description | `--body-file` — markdown |
| Acceptance criteria | `--criteria-file` — appended to the body under `## Acceptance Criteria`, because an issue has no field for them (`schema.md`) |
| Labels | `--label`, repeatable, plus the label for the type |

The type becomes a label, since this source has no type field. The canonical-to-native table is in `types.md`; a `task` has no label and is created unlabelled, which reads back as `task`. The created type is recorded in `ticket.json`.

Assignee, milestone and project are out of scope. So is a parent: an issue has no typed parent link, so `--parent` is not accepted here.
