# Examples — ticket-implement

`/ticket-implement <ref> [phases | all]`

`<ref>` is required; without phases, it shows the Progress table with its Ready column and asks which to run.

| Invocation                        | Implements                                |
| --------------------------------- | ----------------------------------------- |
| `/ticket-implement ado:18585`     | asks which phases, after showing progress |
| `/ticket-implement ado:18585 2`   | phase 2                                   |
| `/ticket-implement ado:18585 1,3` | phases 1 and 3, one after the other       |
| `/ticket-implement ado:18585 all` | every phase not yet done, in number order |

**Refuses:** a ticket with no plan yet, or a plan in the old single-file format — `/ticket-plan` converts it.
