# ado — links

Read by `ticket-digest`, `ticket-plan` and `ticket-checkpoint`.

`{org}` and `{project}` come from `ticket-json`'s `url` where one is already recorded; otherwise they are the `organization` and `project` in this source's config. **Prefer `ticket.json.url` when it is set** — it was written by the fetch that produced the data being linked.

| Reference | Pattern |
| --- | --- |
| Work item | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}` |
| Comment | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}#{comment-id}` |
| Attachment | the **local downloaded file**; the remote `url` from the raw data only as a fallback |

## Attachments link locally

Always prefer the local copy. Where an attachment's `download_ok` is `true`, link to it as a path relative to the file doing the linking — `digest.md`, `plan.md` and `journal.md` all sit in the ticket root, so that path is `raw/{local_filename}`.

Fall back to the remote URL only where `download_ok` is `false` and no local file exists.

## A project name may need encoding

Project names contain dots and can contain spaces. Percent-encode the segment when building a URL by hand rather than pasting the raw name.
