# github — fetch

Read by `ticket-fetch`.

## What lands in `raw/`

```
{ticket-dir}/raw/raw.json     the issue and its full comment thread
```

One file. No attachment files — see the gap below.

```
{
  "meta":     { "repository", "issue_number", "related_supported": false },
  "issue":    { … the issue as the API returns it },
  "comments": [ … every comment, in API order ]
}
```

Both calls go through the GitHub CLI, so the credential is whatever `gh` already holds.

## Comments are paginated

A thread longer than one page is fetched in full and flattened into a single array. A fetch that silently stopped at the first page would produce a digest that looks complete and is not — which is the failure mode this whole suite is built to avoid.

## Two declared gaps

**`capabilities.related` is `false`.** GitHub has no typed link structure between issues: a reference is prose in a body or a comment, and the timeline that records cross-references does not say *what kind* of relationship it is. Rather than guess a parent/child/related shape that the data does not carry, this source declares the capability absent and the digest omits the section. Any references the author wrote are still visible in the body and comments, as prose.

**`capabilities.attachments` is `false`.** An uploaded file appears in an issue body as a markdown link to a user-content URL, with no enumerable attachment list and no reliable way to tell an upload from any other link. Nothing is downloaded, and nothing is reported as a failed download — there was no list to fail at.

Both are gaps to report, not gaps to work around.

## Re-fetch behaviour

`raw.json` is always re-downloaded and replaced wholesale. There are no attachment files to keep, so the "keep what is on disk" rule has nothing to act on here — it is not being violated, there is simply nothing in its scope.

A failed call aborts rather than writing a partial file.

## What `ticket.json` is refreshed with

| Key | From |
| --- | --- |
| `title`, `state` | the issue |
| `type`, `native_type` | resolved per `types.md`; `native_type` records the labels |
| `url` | the issue's own web address |
| `last_fetched_at` | the moment the fetch completed, UTC |
| `fingerprint` | the issue's last-updated timestamp and its comment count, which `drift.md` compares against |

## Upstream is never modified

Fetching is read-only.
