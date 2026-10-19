# Examples — ticket-update

`/ticket-update <ref> [change]`

The ref is required; the change is described in words and shown back as a before and after before anything is written.

| Invocation                                                   | Changes                                             |
| ------------------------------------------------------------ | --------------------------------------------------- |
| `/ticket-update gh:42 "retitle to Export invoices as CSV"`   | the title, after showing the diff and getting a yes |
| `/ticket-update ado:18692 "close it"`                        | the state                                           |
| `/ticket-update gh:42 "add the billing label"`               | the labels                                          |
| `/ticket-update ado:18692 "tag it api, remove spike"`        | the tags, read and rewritten as one list            |
| `/ticket-update ado:18692 "replace the acceptance criteria"` | the acceptance criteria, with the text you supply   |

**Refuses:** a ticket that changed upstream since it was fetched, and a source with no `update` capability. Nothing is written until you answer yes to the before and after.
