# Examples — ticket-implement

`/ticket-implement <ref> [phases | all]`

`<ref>` is required; without phases, it shows the progress table and asks which to run.

| Invocation                        | Implements                                |
| --------------------------------- | ----------------------------------------- |
| `/ticket-implement ado:18585`     | asks which phases, after showing progress |
| `/ticket-implement ado:18585 2`   | phase 2                                   |
| `/ticket-implement ado:18585 1,3` | phases 1 and 3, in order                  |
| `/ticket-implement ado:18585 all` | every phase not yet done, in order        |

**Refuses:** a ticket with no `plan.md` yet.
