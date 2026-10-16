# github — links

Read by `ticket-fetch`, `ticket-plan` and `ticket-digest` to read an address, and by `ticket-digest`, `ticket-plan` and `ticket-checkpoint` to build one.

| Reference  | Pattern                                                                       |
| ---------- | ----------------------------------------------------------------------------- |
| Issue      | `https://github.com/{owner}/{name}/issues/{number}`                           |
| Comment    | `https://github.com/{owner}/{name}/issues/{number}#issuecomment-{comment-id}` |
| Attachment | **none** — nothing is downloaded; link to the URL as written in the body      |

## Prefer the recorded URL

`ticket.json`'s `url` is the issue's own address as the API reported it, recorded at fetch time. **Prefer it over building one by hand** — it is correct on an enterprise host, where the domain is not the public one.

The patterns above are the fallback, and they assume the public host. Take `{owner}/{name}` from `ticket.json`'s `coordinates` — `owner` and `repository` — or else the `coordinates` the resolver reports.

## Reading an address

`resolve` never reads an address; the driver does, into `github:{number}` plus `--coordinate owner={owner} --coordinate repository={repository}`.

| Form                                                      | Is                                                                                                         |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `https://github.com/{owner}/{repository}/issues/{number}` | an issue. `http`, `www.`, a trailing slash, a query, a fragment or a comment anchor all name the same one |
| `{owner}/{repository}#{number}`                           | an issue, in that repository                                                                               |
| `#{number}`, or a bare number                             | an issue in the product the session is in; pass `github:{number}` and no coordinates                       |
| `https://github.com/{owner}/{repository}/pull/{number}`   | **not an issue** — say so and stop. A pull request is recorded with `ticket.py pulls add`                  |

An address on another host is an enterprise instance: take `{owner}` and `{repository}` the same way. The ticket is recorded under the address the API reports, whichever form was pasted, and the repository's own binding files it; a repository that is not bound yet is reported with how to bind it.

## A comment anchor needs the comment's id

Not its position in the thread. The id is on each comment in the fetched data.

## Cross-repository references

`owner/name#123` in a body refers to a different repository. Render it as a link where it is useful, but that ticket is **not** something this suite can resolve: cross-repository references are out of scope, and no local data exists for one.
