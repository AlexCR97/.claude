---
name: az-workitem-implement
description: Deprecated alias for ticket-implement with source=ado. Use /ticket-implement ado:{id} instead.
argument-hint: "<id> [phases]"
disable-model-invocation: true
---

This skill is a **deprecated alias**. It contains no logic of its own: it prefixes the work item ID with the `ado:` source
and hands off to `ticket-implement`.

1. Take the work item ID from the invocation. If none was given, ask for one — there is no inference from the branch name.
2. Tell the user, in **exactly one line**:

   > `/az-workitem-implement {id}` is now `/ticket-implement ado:{id}`. Running it for you.

3. Invoke the real skill, passing every other argument through unchanged:

   ```
   Skill: ticket-implement
   args: ado:{id} {phases}
   ```

Add nothing else — no summary, no extra explanation, no deprecation paragraph.
