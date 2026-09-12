---
name: az-workitem-init
description: Deprecated alias for ticket-init with source=ado. Use /ticket-init ado instead.
argument-hint: "[organization] [project]"
disable-model-invocation: true
---

This skill is a **deprecated alias**. It contains no logic of its own: it names the `ado` source
and hands off to `ticket-init`.

1. Take the organization and project from the invocation, if any were given. Never ask for either — they have defaults.
2. Tell the user, in **exactly one line**:

   > `/az-workitem-init` is now `/ticket-init ado`. Running it for you.

3. Invoke the real skill, passing every other argument through unchanged:

   ```
   Skill: ticket-init
   args: ado {organization} {project}
   ```

The suite is now `ticket-*` and supports Azure DevOps, GitHub and local tickets — see `skills/ticket-init/workflow.md`.

Add nothing else — no summary, no extra explanation, no deprecation paragraph.
