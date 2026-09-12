# github — publish

Read by `ticket-refine`.

## Where a refinement summary goes

A comment on the issue thread, posted through:

```
python "{skills}/ticket-common/ticket.py" publish {source}:{id} --file "{comment-file}" --delete-after-post
```

which routes through the GitHub CLI's own comment command, so the credential is whatever `gh` already holds. `--delete-after-post` removes the staged file once the post is confirmed; do not delete it by hand, because if the post fails that file is what a retry uses.

## Markup: markdown

Write the staged file as `.md`, and write actual markdown.

**Do not write HTML here.** Much of it would render, but headings, tables and lists come out inconsistently against the surrounding markdown and the result reads as if it were pasted in from somewhere else. Markdown is the native form of every other comment in the thread.

The summary is a top-level comment rather than a fragment inside a larger document, so `##` headings for its own sections are correct.

## Template

`{provider-dir}/refinement-template.md`.

Replace every `{placeholder}` with the value derived from the interview. Omit the Open Items heading and its content when everything was resolved.

## After posting

The comment changes the thread, so the local snapshot is stale. This source supports `fetch`, so a re-fetch is the correct follow-up — and it is worth confirming on the web that the comment rendered as markdown rather than as escaped source.
