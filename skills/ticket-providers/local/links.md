# local — links

Read by `ticket-digest`, `ticket-plan` and `ticket-checkpoint`.

| Reference  | Pattern                                          |
| ---------- | ------------------------------------------------ |
| Ticket     | **none** — this store has no web address         |
| Comment    | **none**                                         |
| Attachment | the local file, relative to the linking document |

## There is no ticket URL

`ticket.json`'s `url` is `null` for every ticket here, and that is the correct value rather than a gap to fill.

**Write the title as plain text.** Do not fabricate a `file://` path: it would not survive being shared, it would not resolve on another machine, and it would turn a clean absence into a link that looks broken.

```
# Ticket Digest — #cache-authorization-lookup: Cache the authorization lookup
```

## Attachments link locally

`digest.md` and `journal.md` sit in the ticket directory, so a file the user dropped into `raw/` is linked from them as `raw/{filename}`; `plan/plan.md` and each phase file sit one level down and link it as `../raw/{filename}`. There is no remote fallback, because there is no remote.

## Cross-references between local tickets

A sibling ticket filed in the same product is at `../{slug}/`, so its digest is `../{slug}/digest.md`. A ticket of another source in the same product is at `../../{source}/{id}/`, and one filed in another product at `../../../../{namespace}/{product}/{source}/{id}/`. Use a link only where the target actually exists — this store has no link table to validate against — and prefer one within the product, since a link across products breaks whenever either ticket is re-filed.

**This depth applies only to a file in the ticket directory** — `digest.md`, `journal.md`. From `plan/plan.md` or a phase file, add one `../`. A link written *inside* `raw/ticket.md` itself is one level deeper and needs `../../{slug}/raw/ticket.md`, never `../{slug}/` and never `[[{slug}]]` wiki syntax — see `schema.md`'s *"Writing a link to another local ticket"*.
