---
name: az-workitem-plan
description: Deprecated alias for ticket-plan with source=ado. Use /ticket-plan ado:{id} instead.
argument-hint: "<id>"
disable-model-invocation: true
---

This skill is a **deprecated alias**. It contains no logic of its own: it prefixes the work item ID with the `ado:` source
and hands off to `ticket-plan`.

1. Take the work item ID from the invocation. If none was given, ask for one — there is no inference from the branch name.
2. Tell the user, in **exactly one line**:

   > `/az-workitem-plan {id}` is now `/ticket-plan ado:{id}`. Running it for you.

3. Invoke the real skill, passing every other argument through unchanged:

   ```
   Skill: ticket-plan
   args: ado:{id}
   ```

Add nothing else — no summary, no extra explanation, no deprecation paragraph.
