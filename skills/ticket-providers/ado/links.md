# ado — links

Read by `ticket-digest`, `ticket-plan` and `ticket-checkpoint`.

`{org}` and `{project}` come from `ticket.json`'s `url` where one is already recorded; otherwise from its `coordinates`, then the `coordinates` the resolver reports — the binding of the product it is filed under. **Prefer `ticket.json.url` when it is set** — it was written by the fetch that produced the data being linked.

| Reference  | Pattern                                                                              |
| ---------- | ------------------------------------------------------------------------------------ |
| Work item  | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`                         |
| Comment    | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}#{comment-id}`            |
| Attachment | the **local downloaded file**; the remote `url` from the raw data only as a fallback |

## Attachments link locally

Always prefer the local copy. Where an attachment's `download_ok` is `true`, link to it as a path relative to the file doing the linking — `raw/{local_filename}` from `digest.md` and `journal.md`, which sit in the ticket directory, and `../raw/{local_filename}` from `plan/plan.md` and each phase file, one level down.

Fall back to the remote URL only where `download_ok` is `false` and no local file exists.

## A project name may need encoding

Project names contain dots and can contain spaces. Percent-encode the segment when building a URL by hand rather than pasting the raw name.
