# Examples — ticket-new

`/ticket-new <title> [--source source] [--type type] [--in namespace[/product]] [--parent ref]`

`<title>` is required and quoted when it has spaces; every flag is optional and order-independent.

| Invocation                                                             | Creates                                                       |
| ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| `/ticket-new "Cache the authorization lookup"`                         | a ticket in the only store that can create one; asks its type |
| `/ticket-new "Cache the authorization lookup" --type tech-debt`        | a ticket of that type                                         |
| `/ticket-new "Pick a queue library" --type spike --in acme/web`        | a ticket filed under that product                             |
| `/ticket-new "Add the export endpoint" --type task --parent ado:18585` | a task linked to its parent user story                        |
| `/ticket-new "Fix the date picker" --source local --type bug`          | a ticket in the named store                                   |

**Refuses:** a source that cannot create tickets, such as a remote one.
