# Examples — ticket-resume

`/ticket-resume [ref]`

One optional argument: without it, the tickets on disk are listed, most recently touched first, and it asks which to resume.

| Invocation                          | Resumes                                         |
| ----------------------------------- | ----------------------------------------------- |
| `/ticket-resume`                    | lists the tickets on disk and asks which        |
| `/ticket-resume ado:18159`          | the nearest ticket of that name                 |
| `/ticket-resume acme/web/ado:18159` | exactly that ticket, by its qualified reference |
