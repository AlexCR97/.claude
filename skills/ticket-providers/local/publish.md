# local — publish

Read by `ticket-refine`.

## Applied in place, not posted as a comment

There is no discussion thread here that means anything — `raw/ticket.md` *is* the ticket, not a copy of one — so a refinement's conclusions are written directly into the two sections `/ticket-new` left as `TODO` stubs for exactly this:

| Template section                                                      | Lands in                                                                |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `Goal and Success Criteria`                                           | `## Acceptance Criteria` — replaces its content wholesale               |
| `Domain Model and Data`, `Edge Cases and Failure Modes`, `Open Items` | `## Description` — folded together, each keeping its own `####` heading |

`## Comments` is never touched by this verb.

**A section still holding its original stub is replaced outright.** A section a person has already written into is grown instead — the new content is appended after what is there, never overwriting hand-written prose. This is why a ticket refined more than once keeps every pass's conclusions rather than only the latest.

**Every leftover `TODO — ...` marker in that section is stripped first**, whichever section it grows onto. `/ticket-new`'s type-seeded stubs routinely leave more than one — a bolded question per "what refine must establish" item, each ending in its own `TODO — run /ticket-refine to establish this.` — and a refinement pass answering one is exactly the moment its marker stops being true. Only the marker sentence goes; a bolded question or a "Provisionally: ..." guess sitting next to it survives as context. A line that was nothing but a marker (a bare paragraph, or a bullet with nothing else in it) is dropped entirely rather than left as a dangling `-`.

Posted through:

```
python "{skills}/ticket-common/ticket.py" publish {source}:{id} --file "{comment-file}" --delete-after-post
```

The verb name and the staged filename (`refinement-comment.{ext}`) are the driver's generic vocabulary for "the confirmed summary" — inherited from the sources that really do post a comment. Nothing here is actually appended to a comment thread.

## Markup: markdown, no nesting required

The body is markdown, like the rest of the file. Write the staged file as `.md`.

**The summary is not appended inside another section**, so it does not need to nest below anything: write it at the heading levels `refinement-template.md` already uses. Do not add a title heading — the template's `####` lines are already the summary's own headings.

## Template

`{provider-dir}/refinement-template.md`, which is already written at the right level.

Replace every `{placeholder}` with the value derived from the interview. Omit the Open Items heading and its content when everything was resolved.

## After posting

The drift fingerprint moves with the file, so the refinement does not read as someone else's edit on the next resume.

**There is nothing to re-fetch.** The summary was written straight into the source of truth — this source has no `fetch`, and there is no upstream copy that could now be ahead of the local one.
