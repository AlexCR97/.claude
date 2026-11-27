---
name: fact-check
description: Re-verifies the facts a conversation, ticket, spec, document or file established earlier. Checks each testable claim live, read-only, and reports verdicts with evidence. Use on "is this still true", "has anything changed since", "check my assumptions".
argument-hint: "[path | url | ticket-reference]"
---

Re-checks what earlier work took as true, for a user who comes back to it after days or weeks. Time and other people's changes move code, tickets, pull requests, versions and environments.

End state: one report in the chat that gives a verdict and the evidence for every claim checked, and lists the conclusions that rest on a claim that no longer holds. Nothing is written, edited or changed.

## Parameters

- **`[path | url | ticket-reference]`** — the source to re-verify: a file, a page, or a GitHub issue, pull request or Azure DevOps work item. Defaults to the current conversation. A document name is a path. Never infer a ticket from the branch name: a wrong guess checks the wrong work.

## Ground rules

1. **Read only.** Never edit the source, and never run a command that writes, deletes, deploys or sends. A claim that only a write could check is `Can't verify`.
2. **Look up every claim again.** Memory, earlier output and the source's own text are not evidence. Run the check now.
3. **Never pass what you could not check.** A claim without a live check is `Can't verify`. It is never `Holds`.
4. **Protect environments.** Apply the session's instructions on which environments run unprompted. Treat an environment that is not clearly non-production as production and do not contact it. Report the claims it leaves `Can't verify`.
5. **Report every gap.** Report each claim skipped and each check that could not run. A report that implies full coverage is wrong.

## Execution Steps

### Step 1 — Resolve the source

Resolve the argument and read all of the source:

- **Omitted:** the current conversation, including the tool output in it.
- **A file:** read it in full.
- **A GitHub or Azure DevOps reference or URL:** read the ticket, its comments and its relations with `gh` or `az`.
- **Another URL:** fetch the page.

Report the source in one line.

A source you cannot read stops the run: report why and ask for another.

### Step 2 — Extract the claims

List every claim the source asserts that a check can test now:

| Kind                   | Example                                                                |
| ---------------------- | ---------------------------------------------------------------------- |
| Code or file           | "`Orders.Total` ignores tax", "the config lives in `appsettings.json`" |
| Behavior               | "the endpoint returns 404 for an unknown id"                           |
| Ticket or pull request | "the pull request is open", "the ticket is blocked by AB#123"          |
| Version                | "the service targets .NET 8"                                           |
| Assumption             | "no other caller uses this method"                                     |

Record each claim's age: the time of the message, comment, journal entry or file. Write `unknown` when the source holds none.

Skip decisions, preferences and opinions. When a decision rests on a claim from the list, note the decision beside that claim for Step 5.

When the list is empty, report `No testable claims in {source}.` and stop.

### Step 3 — Classify the claims

Mark each claim:

| Class    | Meaning                                                                                              | Checked                      |
| -------- | ---------------------------------------------------------------------------------------------------- | ---------------------------- |
| Volatile | Moves on its own: branch and pull request state, ticket state, dependency versions, environment data | Always, live                 |
| Stable   | Rarely moves: language semantics, published contracts                                                | Only when the check is cheap |

Group related claims into code, tickets and pull requests, and environment. Mark a claim that needs another claim to hold first as dependent on it.

### Step 4 — Verify

Check each claim the way its kind needs. Take the verdict from what the check returned.

| Verdict        | Meaning                                              |
| -------------- | ---------------------------------------------------- |
| `Holds`        | The check confirms the claim as written.             |
| `Changed`      | The subject exists and now differs from the claim.   |
| `Gone`         | The subject no longer exists.                        |
| `Can't verify` | No allowed check settles it. Report what is missing. |

- **10 claims or fewer:** check them in this session.
- **More than 10:** start one read-only `Explore` sub-agent per group, in parallel. Give each the claim text and where it came from. Never give it the verdict you expect. Ask for a verdict and the evidence for each claim, one line each.
- **Dependent claims:** check them in order. When the first one fails, mark the claims that rest on it `Can't verify`, not `Holds`.

Evidence names the command or file read and what it returned.

### Step 5 — Report

Report in one message, with these parts in this order:

1. **Headline:** `N claims checked: A hold, B changed, C gone, D can't verify`.
2. **Table** with the columns Claim, Verdict, Evidence and Age. Order the rows `Gone`, `Changed`, `Can't verify`, `Holds`.
3. **What this invalidates:** for each `Changed` or `Gone` claim, the conclusions and decisions in the source that rest on it, each marked **premise changed** and quoted with its location. Omit this part when nothing rests on such a claim.
4. **Gaps:** the claims skipped and the checks that could not run (ground rule 5). Omit this part when there are none.

Do not propose edits or fixes. The user decides what to update.
