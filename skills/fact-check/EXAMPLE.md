# Examples — fact-check

`/fact-check [path | url | ticket-reference]`

The argument is optional. Omitted, it re-verifies the current conversation.

| Invocation                   | Re-verifies                                   |
| ---------------------------- | --------------------------------------------- |
| `/fact-check`                | the claims made earlier in this conversation  |
| `/fact-check docs/spec.md`   | the claims in that file                       |
| `/fact-check AB#19078`       | the claims in that work item and its comments |
| `/fact-check issue#12`       | the claims in that GitHub issue               |
| `/fact-check https://…/page` | the claims on that page                       |

**Refuses:** a source it cannot read, and any request to update or fix the source.
