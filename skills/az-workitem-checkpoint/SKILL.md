---
name: az-workitem-checkpoint
description: Deprecated alias for ticket-checkpoint with source=ado. Use /ticket-checkpoint ado:{id} instead.
argument-hint: "[id] [note]"
disable-model-invocation: true
---

This skill is a **deprecated alias**. It contains no logic of its own: it prefixes the work item ID with the `ado:` source
and hands off to `ticket-checkpoint`.

1. Take the work item ID from the invocation. If none was given, ask for one — there is no inference from the branch name.
2. Tell the user, in **exactly one line**:

   > `/az-workitem-checkpoint {id}` is now `/ticket-checkpoint ado:{id}`. Running it for you.

3. Invoke the real skill, passing every other argument through unchanged:

   ```
   Skill: ticket-checkpoint
   args: ado:{id} {note}
   ```

Add nothing else — no summary, no extra explanation, no deprecation paragraph.
