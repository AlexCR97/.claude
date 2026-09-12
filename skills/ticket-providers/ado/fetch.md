# ado — fetch

Read by `ticket-fetch`.

## What lands in `raw/`

```
{ticket-dir}/raw/raw.json          all API data, always refreshed
{ticket-dir}/raw/{guid}.{ext}      attachment files
{ticket-dir}/raw/{guid}/           a downloaded archive, extracted beside it
```

`raw.json` is source-shaped — it is what the API returned, verbatim, nested in a tree. `schema.md` is what tells the digest where to find things in it.

```
{
  "meta":  { "organization", "project", "work_item_id", "max_depth", "total_work_items_fetched" },
  "tree":  {
    "id",
    "work_item":  { … the full work item response, including "fields" and "rev" },
    "discussion": { "comments": [ … ] },
    "attachments": [ … ],
    "related":     [ { "relation_type": "parent"|"child"|"related", … same shape, recursively } ]
  }
}
```

## Traversal policy

Related work items are resolved recursively to a maximum depth of **3**. Already-visited ids are tracked so a cycle cannot loop.

Which relations are followed depends on the root work item's own type:

| Root type | Relations expanded |
| --- | --- |
| Task | `parent` only |
| Everything else | `parent`, `child`, `related` |

A Task's children and siblings are almost never the context its own work needs, and expanding them pulls in the whole sprint.

A node that was not expanded is still recorded, with a `skipped_reason` of `traversal_policy`, `already_visited`, `max_depth_reached`, or `fetch_failed`. Nothing is silently dropped.

## Attachments

Two kinds, and the second is the one that is easy to miss:

- **`AttachedFile` relations** — files attached to the work item proper.
- **Inline references** — an image pasted into a description, acceptance criteria or a comment is embedded as inline HTML and is **not** exposed as an `AttachedFile` relation. Every HTML field and every comment body is scanned for `/_apis/wit/attachments/…` URLs in `src` or `href`, or those attachments are lost.

One attachment can surface from both at once with different URLs, so they are deduplicated on the attachment GUID rather than on the URL.

**On-disk naming is the GUID plus the original extension**, because ADO names every pasted screenshot `image.png` and original names collide constantly. Keying on the GUID makes the name unique by construction and stable across runs, so a digest written earlier keeps pointing at the right file even if images are later added or reordered. The original name stays in the attachment's `name` field for display.

Each attachment record carries `local_filename` (null when the download failed) and `download_ok`. A ZIP is extracted into a sibling directory named after its stem.

## Re-fetch behaviour

- `raw.json` is **always** re-downloaded.
- Naming is deterministic, so **a file already on disk is the same attachment and is kept, not re-downloaded**.
- Only new or missing attachments are downloaded.
- A 401 mid-fetch **aborts** rather than writing a partial `raw/`: every later call would fail the same way and leave a snapshot that reads as complete.

## What `ticket.json` is refreshed with

| Key | From |
| --- | --- |
| `title`, `state` | the root work item's fields |
| `type`, `native_type` | resolved per `types.md` |
| `url` | per `links.md` |
| `last_fetched_at` | the moment the fetch completed, UTC |
| `fingerprint.rev` | the work item revision, which `drift.md` compares against |

## Upstream is never modified

Nothing in this path writes to Azure DevOps. Fetching is read-only, including the recursive walk.
