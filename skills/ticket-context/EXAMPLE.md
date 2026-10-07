# Examples — ticket-context

`/ticket-context [namespace[/product] | clear]`

One optional argument: a namespace or product sets the context, `clear` clears it, and none shows it.

| Invocation                 | Session context                                              |
| -------------------------- | ------------------------------------------------------------ |
| `/ticket-context`          | shows the current one                                        |
| `/ticket-context acme/web` | set to that product                                          |
| `/ticket-context acme`     | set to that namespace; new tickets go to its default product |
| `/ticket-context clear`    | cleared                                                      |

**Refuses:** a namespace or product that does not exist.
