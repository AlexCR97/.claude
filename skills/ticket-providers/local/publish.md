# local — publish

Read by `ticket-refine`.

## Where a refinement summary goes

Appended under the `## Comments` section of `{ticket-dir}/raw/ticket.md`, as a block headed:

```
### {YYYY-MM-DD HH:MM} UTC — Refinement Session
```

The section is created if the file does not have one. Posted through:

```
python "{skills}/ticket-common/ticket.py" publish {source}:{id} --file "{comment-file}" --delete-after-post
```

## Markup: markdown, at a nested heading level

The body is markdown, like the rest of the file. Write the staged file as `.md`.

**The summary is a fragment, not a document.** It is appended *inside* a section of an existing file, so its headings have to nest below the ones already there:

| Level | Used by |
| --- | --- |
| `#` | the ticket's own title |
| `##` | the file's sections — `Description`, `Acceptance Criteria`, `Comments`, `Links` |
| `###` | one comment |
| `####` | **the summary's own sections** |

A summary written with `##` headings would not sit *in* the comment — it would silently end the `## Comments` section and turn each of its parts into a new top-level section of the ticket. Nothing errors; the file just quietly stops meaning what it says. Do not add a title heading either: the `###` line the append generates is already the summary's heading.

## Template

`{provider-dir}/refinement-template.md`, which is already written at the right level.

Replace every `{placeholder}` with the value derived from the interview. Omit the Open Items heading and its content when everything was resolved.

## Appending, never rewriting

Only the new block is added; the rest of the file is left byte-for-byte as it was. Everything else in it was written by a person, and a publish must not reflow their prose or renumber their headings.

## After posting

The drift fingerprint moves with the file, so the refinement does not read as someone else's edit on the next resume.

**There is nothing to re-fetch.** The summary was written straight into the source of truth — this source has no `fetch`, and there is no upstream copy that could now be ahead of the local one.
