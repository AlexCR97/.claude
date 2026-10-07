# Examples — ticket-move

`/ticket-move <ref> <namespace/product>`

Both arguments are positional; each one omitted is asked for.

| Invocation                                             | Re-files                                                |
| ------------------------------------------------------ | ------------------------------------------------------- |
| `/ticket-move`                                         | asks for the ticket and the destination                 |
| `/ticket-move ado:18585 acme/web`                      | that ticket under `acme/web`, after a dry run and a yes |
| `/ticket-move default/default/local:auth-fix acme/web` | exactly that ticket, by its qualified reference         |

**Refuses:** a destination bound to other coordinates than the ticket's, or already holding a ticket of that id.
