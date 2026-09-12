# github — links

Read by `ticket-digest`, `ticket-plan` and `ticket-checkpoint`.

| Reference | Pattern |
| --- | --- |
| Issue | `https://github.com/{owner}/{name}/issues/{number}` |
| Comment | `https://github.com/{owner}/{name}/issues/{number}#issuecomment-{comment-id}` |
| Attachment | **none** — nothing is downloaded; link to the URL as written in the body |

## Prefer the recorded URL

`ticket.json`'s `url` is the issue's own address as the API reported it, recorded at fetch time. **Prefer it over building one by hand** — it is correct on an enterprise host, where the domain is not the public one.

The patterns above are the fallback, and they assume the public host. Take `{owner}/{name}` from this source's config.

## A comment anchor needs the comment's id

Not its position in the thread. The id is on each comment in the fetched data.

## Cross-repository references

`owner/name#123` in a body refers to a different repository. Render it as a link where it is useful, but that ticket is **not** something this suite can resolve: cross-repository references are out of scope, and no local data exists for one.
