# Examples — ticket-checkpoint

`/ticket-checkpoint [ref] [note]`

Both are optional: without a ref it takes the ticket this session worked on, or asks; a note, quoted, is folded into the entry.

| Invocation                                                           | Records                                  |
| -------------------------------------------------------------------- | ---------------------------------------- |
| `/ticket-checkpoint`                                                 | this session's ticket, or asks which one |
| `/ticket-checkpoint ado:18585`                                       | that ticket                              |
| `/ticket-checkpoint ado:18585 "stopping to review the PR for 18201"` | that ticket, with the note folded in     |
