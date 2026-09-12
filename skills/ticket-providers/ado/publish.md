# ado — publish

Read by `ticket-refine`.

## Where a refinement summary goes

A comment on the work item's discussion thread, posted through:

```
python "{skills}/ticket-common/ticket.py" publish {source}:{id} --file "{comment-file}" --delete-after-post
```

`--delete-after-post` removes the staged file once the post is confirmed. Do not delete it by hand — if the post fails, the file is what the retry uses.

## Markup: HTML, and only HTML

**The ADO discussion renderer accepts HTML only.** A markdown body posted here arrives as escaped source rather than formatting — the reader sees `**Goal**` rather than bold text, and a table becomes a wall of pipes. This is not a style preference; it is what the destination renders.

Write the staged file as `.html`, and produce valid HTML rather than markdown.

## Template

`{provider-dir}/refinement-template.html`.

Replace every `{placeholder}` with the value derived from the interview. Omit the Open Items `<h2>` and its content when everything was resolved.

The template's `<br>`, `<hr>` and `&mdash;` entities are not decoration — the ADO renderer collapses whitespace and ignores markdown-style separators, so spacing has to be explicit.

## After posting

The comment just posted changes the discussion, so the local snapshot is stale. This source supports `fetch`, so a re-fetch is the correct follow-up.
