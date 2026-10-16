# ado — links

Read by `ticket-fetch`, `ticket-plan` and `ticket-digest` to read an address, and by `ticket-digest`, `ticket-plan` and `ticket-checkpoint` to build one.

`{org}` and `{project}` come from `ticket.json`'s `url` where one is already recorded; otherwise from its `coordinates`, then the `coordinates` the resolver reports — the binding of the product it is filed under. **Prefer `ticket.json.url` when it is set** — it was written by the fetch that produced the data being linked.

| Reference  | Pattern                                                                              |
| ---------- | ------------------------------------------------------------------------------------ |
| Work item  | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`                         |
| Comment    | `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}#{comment-id}`            |
| Attachment | the **local downloaded file**; the remote `url` from the raw data only as a fallback |

## Reading an address

`resolve` never reads an address; the driver does, into `ado:{id}` plus `--coordinate organization={org} --coordinate project={project}`. Percent-decode the project: `EW.Educate`, never `EW%2EEducate`.

| Form                                                             | Is                                                                                                   |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `https://dev.azure.com/{org}/{project}/_workitems/edit/{id}`     | a work item. A query or a fragment such as a comment anchor changes nothing                          |
| `https://{org}.visualstudio.com/{project}/_workitems/edit/{id}`  | the same, on the older host                                                                          |
| `…/_boards/board/…?workitem={id}`, `…/_backlogs/…?workitem={id}` | the work item `{id}`, open on a board or a backlog, in the `{org}` and `{project}` the address names |
| `https://dev.azure.com/{org}/{project}/_git/…/pullrequest/{n}`   | **not a work item** — say so and stop                                                                |
| a bare number, or `#{id}`                                        | a work item; pass `ado:{id}` and no coordinates                                                      |

An id is unique within an organization, not a project, so the project an address names need not be the one the work item lives in. Pass what the address says; the fetch records where it really is, and reports `misfiled` if the product it was filed under disagrees.

## Attachments link locally

Always prefer the local copy. Where an attachment's `download_ok` is `true`, link to it as a path relative to the file doing the linking — `digest.md` and `plan.md` sit in the ticket directory, so that path is `raw/{local_filename}`; a journal entry sits one level down, so its path is `../raw/{local_filename}`.

Fall back to the remote URL only where `download_ok` is `false` and no local file exists.

## A project name may need encoding

Project names contain dots and can contain spaces. Percent-encode the segment when building a URL by hand rather than pasting the raw name.
