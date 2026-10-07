# Examples — ticket-refine

`/ticket-refine <ref> [--type type]`

`<ref>` is required; `--type` overrides the resolved type and is recorded for the skills that follow.

| Invocation                               | Refines                                           |
| ---------------------------------------- | ------------------------------------------------- |
| `/ticket-refine ado:18585`               | that ticket, as its resolved type                 |
| `/ticket-refine acme/web/local:auth-fix` | exactly that ticket, by its qualified reference   |
| `/ticket-refine ado:18585 --type spike`  | that ticket as a spike, recorded in `ticket.json` |

**Refuses:** a ticket with nothing fetched yet.
