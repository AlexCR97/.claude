# Examples — ticket-plan

`/ticket-plan <ref> [dir ...] [--type type]`

`<ref>` is required; each `dir` is a scan root added to the default scan roots; `--type` overrides the resolved type.

| Invocation                                  | Plans                                                    |
| ------------------------------------------- | -------------------------------------------------------- |
| `/ticket-plan ado:18585`                    | from the default scan roots, or the invocation directory |
| `/ticket-plan ado:18585 C:\src\billing-api` | with that worktree as a scan root                        |
| `/ticket-plan ado:18585 --type spike`       | in a spike's shape, recorded in `ticket.json`            |

**Refuses:** a ticket with no `digest.md` yet; and regenerating or renumbering while any phase is `In Progress`.
