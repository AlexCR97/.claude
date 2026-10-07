# Examples — ticket-digest

`/ticket-digest <ref> [--type type]`

`<ref>` is required; `--type` overrides the resolved type and is recorded for the skills that follow.

| Invocation                               | Digests                                         |
| ---------------------------------------- | ----------------------------------------------- |
| `/ticket-digest ado:18585`               | that ticket, as its resolved type               |
| `/ticket-digest acme/web/local:auth-fix` | exactly that ticket, by its qualified reference |
| `/ticket-digest ado:18585 --type bug`    | that ticket as a bug, recorded in `ticket.json` |

**Refuses:** a ticket with nothing fetched yet.
