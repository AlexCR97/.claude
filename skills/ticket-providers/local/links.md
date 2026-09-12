# local — links

Read by `ticket-digest`, `ticket-plan` and `ticket-checkpoint`.

| Reference | Pattern |
| --- | --- |
| Ticket | **none** — this store has no web address |
| Comment | **none** |
| Attachment | the local file, relative to the linking document |

## There is no ticket URL

`ticket.json`'s `url` is `null` for every ticket here, and that is the correct value rather than a gap to fill.

**Write the title as plain text.** Do not fabricate a `file://` path: it would not survive being shared, it would not resolve on another machine, and it would turn a clean absence into a link that looks broken.

```
# Ticket Digest — #cache-authorization-lookup: Cache the authorization lookup
```

## Attachments link locally

`digest.md`, `plan.md` and `journal.md` all sit in the ticket root, so a file the user dropped into `raw/` is linked as `raw/{filename}`. There is no remote fallback, because there is no remote.

## Cross-references between local tickets

A sibling ticket's directory is `../{slug}/`, so its digest is `../{slug}/digest.md`. Use that only where the target actually exists — this store has no link table to validate against.
