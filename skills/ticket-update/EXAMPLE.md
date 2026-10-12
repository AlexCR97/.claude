# Examples — ticket-update

`/ticket-update <ref> [what to change]`

The ref is required; the change is described in words and shown back as a before and after before anything is written.

| Invocation                                                      | Changes                                              |
| --------------------------------------------------------------- | ---------------------------------------------------- |
| `/ticket-update gh:42 "retitle to Export invoices as CSV"`      | the title, after showing the diff and getting a yes  |
| `/ticket-update ado:18692 "close it"`                           | the state                                            |
| `/ticket-update gh:42 "add the billing label"`                  | the labels                                           |
| `/ticket-update ado:18692 "new acceptance criteria from below"` | the acceptance criteria, with the text you supply    |

If the ticket changed upstream since it was fetched, nothing is written and you are told to run `/ticket-fetch` first.
