# local — drift

Read by `ticket-resume`.

```
python "{skills}/ticket-common/ticket.py" drift {source}:{id}
```

Read-only. Nothing is rewritten.

## Exit contract

| Exit | Means |
| --- | --- |
| 0 | the recorded fingerprint matches the file |
| 1 | the comparison could not be made — no ticket body on disk |
| 2 | the file changed since it was last recorded |

## What is compared

**A SHA-256 of `raw/ticket.md`**, against the `fingerprint.sha256` recorded in `ticket.json`.

There is no upstream revision counter to compare against, so the file's own content is the only thing that can say whether it moved. It is a coarse signal — it cannot say *what* changed, only that something did — and that is enough for what a resume does with it: recommend a re-read before continuing.

Alongside it, the frontmatter's `title`, `state` and `type` are compared against what `ticket.json` records, which is the one place this store can say *what* moved.

## Why this is worth having at all

A local ticket is edited by hand, often between sessions and often by the same person who then forgets. A resume that says "the ticket body changed since the digest was written" is exactly as useful here as it is for a remote source — arguably more so, since there is no notification anywhere else.

## A ticket with no recorded fingerprint

Reported as `unfingerprinted`, and **not** as stale. A ticket that predates the fingerprint has not been shown to have changed, and reporting a change nobody made is worse than reporting nothing.
