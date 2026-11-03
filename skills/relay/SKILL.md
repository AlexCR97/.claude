---
name: relay
description: Compiles a quick-glance TL;DR of the session for a manager and copies it as rich text for a chat app such as Teams, Slack or Discord. Use on "for my manager", "exec summary", "status update for <person>", "TL;DR I can send" or "something I can screenshot" — not a plain "summarize".
argument-hint: "[focus]"
allowed-tools: Write PowerShell(powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File:*)
---

Compiles what matters from the current session into a summary a non-technical reader takes in at a glance, then copies it so the user can paste it into a chat app such as Teams, Slack or Discord, or screenshot it from the terminal.

End state: the summary printed in the terminal, the same summary on the clipboard as rich HTML and plain text, and a one-line note that says whether the copy succeeded.

## Parameters

- **`[focus]`** — free text that narrows the summary. It can name a topic (`perf results of the cache change`), a shape (`as a table`), a language (`in Spanish`), or any mix of the three, in any order. Defaults to the session's most consequential outcome, in the shape the content suits, in English.

## Ground rules

1. **Use the session only.** Never run a command to gather or verify a fact. The only commands are the clock read in Step 4 and the clipboard copy in Step 5.
2. **Never invent.** When the session holds no outcome worth relaying, report that and copy nothing.
3. **Leave out secrets and personal data.** Never include a secret, token, password, connection string, internal hostname, IP address or customer personal data. When the key fact is one of these, describe it in general terms and warn the user in the terminal only.
4. **Stay inside the cap.** One screenshot, one glance. Cut content before you exceed a cap in Step 3.
5. **Write content only.** No greeting, no sign-off, no "let me know". The user adds the framing in the chat app.
6. **Copy on every run.** Overwriting the clipboard is the purpose of the skill.

## Execution Steps

### Step 1 — Settle the scope

Read `[focus]` and take from it:

- **Topic** — what to relay. Absent, take the session's most consequential outcome.
- **Shape** — `message`, `list`, `table` or `metrics`. Absent, Step 3 picks one.
- **Language** — absent, English.

Search the session for outcomes inside the topic: work finished, results measured, decisions made, problems found, blockers, next steps.

- **Outcomes found:** continue to Step 2.
- **None found:** report `Nothing in this session to relay.` Stop. Copy nothing (ground rule 2).

### Step 2 — Select the facts

Rank the outcomes by consequence to the reader — what changed for the team, the product or the schedule — not by the effort the session spent on them.

- Take the top outcome as the headline.
- Give each other outcome at most one line. Never split the summary into sections.
- Keep a fact only when the reader needs it to act or to understand the state. Drop mechanics: file paths, code, class names, commands, stack traces, tool names.
- Replace any fact that ground rule 3 forbids with a general description, and record it for the warning in Step 5.

### Step 3 — Pick the shape

Use the shape from Step 1 when it was given. Otherwise pick by content:

| Shape     | Pick when                                        | Cap after the headline |
| --------- | ------------------------------------------------ | ---------------------- |
| `message` | one fact or announcement                         | two sentences          |
| `list`    | several distinct outcomes                        | five bullets           |
| `table`   | several items share attributes, such as a status | six rows, four columns |
| `metrics` | the numbers are the news                         | four metrics           |

Every shape opens with a one-line headline, the TL;DR, and may close with one `➡️ Next:` or `➡️ Ask:` line.

Write each metric as before → after with the relative change, rounded to the precision a manager reads: `p95 latency: 840 ms → 210 ms (−75%)`. A metric with no baseline takes its value alone.

Mark status with this fixed set only, never as decoration:

| Marker | Status                  |
| ------ | ----------------------- |
| ✅      | done                    |
| 🟡      | in progress, or at risk |
| 🔴      | blocked, or failed      |
| ➡️      | next step, or an ask    |

### Step 4 — Write the summary

Read the clock for the footer:

```powershell
$tz = [TimeZoneInfo]::Local; $name = if ($tz.IsDaylightSavingTime((Get-Date))) { $tz.DaylightName } else { $tz.StandardName }; (Get-Date -Format 'MMM d, h:mm tt') + ' ' + -join ($name -split ' ' | Where-Object { $_ -match '^[A-Za-z]' } | ForEach-Object { $_[0] })
```

The output is `{timestamp}`, such as `Nov 3, 2:20 PM CST`. The last line of every rendering is `As of {timestamp}`.

Write in the language from Step 1, for a reader who never saw the session: outcomes and impact, plain words, short lines.

Name a pull request, issue or work item in its platform form with a short title: `#524 (promote enrollment-api to QA)`, `AB#19078 (invoice export)`. Link the form to its full URL in the HTML rendering when the session holds the URL.

Write the summary three times, with the same content in each:

| Rendering  | Goes to                                          | Form                                                                                                                         |
| ---------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Markdown   | the terminal                                     | bold headline, `-` bullets, a pipe table, the footer in italics                                                              |
| HTML       | the clipboard, for chat apps that keep rich text | a fragment of `<p>`, `<b>`, `<ul>`/`<li>`, `<table>`/`<th>`/`<td>`, `<a href>` and `<i>`; no styles, no `<html>` or `<body>` |
| Plain text | the clipboard, elsewhere                         | no markdown symbols; `•` bullets; each table row as one line, `Item — value · value`                                         |

### Step 5 — Copy to the clipboard

Write the HTML rendering to `{html-file}` and the plain text rendering to `{text-file}`, both UTF-8, named `relay-summary.html` and `relay-summary.txt`. Put them in the session's scratchpad directory when the system prompt names one, otherwise in `$env:TEMP`. Overwrite earlier copies.

Run the script:

```powershell
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "{path-to-skill}/copy-to-clipboard.ps1" -HtmlPath "{html-file}" -TextPath "{text-file}"
```

Then report, in this order:

1. The Markdown rendering. Print exactly that content and nothing between its lines.
2. The copy result:
   - **Prints `copied: html+text`:** `📋 Copied to clipboard — rich text for chat apps, plain text elsewhere.`
   - **`powershell.exe` not found:** `Not copied: powershell.exe is not available on this machine.`
   - **Any other failure:** `Not copied:` and the first line of the error.
3. Every fact Step 2 replaced, as `⚠️ Left out: {description}`. This line is never copied.

### Step 6 — Revise on follow-up

When the user's next message changes the summary — `shorter`, `drop the second bullet`, `make it a table`, `add the test results` — apply the change under the same ground rules and caps. Then run Step 4 and Step 5 again, so the terminal and the clipboard hold the revised summary.
