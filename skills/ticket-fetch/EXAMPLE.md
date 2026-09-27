# Examples — ticket-fetch

`/ticket-fetch <ref> [--in namespace[/product]]`

`<ref>` is positional and required; without `--in`, the filing rules choose the product for a ticket not yet on disk.

| Invocation                                                           | Fetches                                                         |
| -------------------------------------------------------------------- | --------------------------------------------------------------- |
| `/ticket-fetch 18585`                                                | the nearest ticket with that id                                 |
| `/ticket-fetch ado:18585`                                            | that id from the named source                                   |
| `/ticket-fetch acme/web/ado:18585`                                   | exactly that ticket, by its qualified reference                 |
| `/ticket-fetch https://dev.azure.com/acme/web/_workitems/edit/18585` | the ticket at that address, filed under the product bound to it |
| `/ticket-fetch 18585 --in acme/web`                                  | a ticket not yet on disk, filed under that product              |

**Refuses:** a source with no remote system, such as a local store.
