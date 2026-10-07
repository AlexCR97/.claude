# Examples — ticket-create

`/ticket-create <title> [--source source] [--type type] [--in namespace[/product]] [--parent ref]`

`<title>` is required and quoted when it has spaces; every flag is optional and order-independent.

| Invocation                                                                | Creates                                                       |
| ------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `/ticket-create "Cache the authorization lookup"`                         | a ticket in the only store that can create one; asks its type |
| `/ticket-create "Cache the authorization lookup" --type tech-debt`        | a ticket of that type                                         |
| `/ticket-create "Pick a queue library" --type spike --in acme/web`        | a ticket filed under that product                             |
| `/ticket-create "Add the export endpoint" --type task --parent ado:18585` | a task linked to its parent user story                        |
| `/ticket-create "Fix the date picker" --source local --type bug`          | a ticket in the named store                                   |

**Refuses:** a source that cannot create tickets, such as a remote one.
