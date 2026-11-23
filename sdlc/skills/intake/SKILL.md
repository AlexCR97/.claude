---
name: intake
description: Brings a unit of work into the sdlc store, from a GitHub issue (a number, owner/repo#n or a URL), an Azure DevOps work item (an id or a URL), a spec file, pasted text or an idea, or the current branch.
disable-model-invocation: true
argument-hint: "[<github issue> | <azure devops work item> | <spec file path> | <text or idea>]"
---

# Intake

Turn what `$ARGUMENTS` holds into a ticket. A GitHub issue or an Azure DevOps work item is mirrored by `fetch`; anything else becomes a new local ticket by following `${CLAUDE_PLUGIN_ROOT}/shared/adoption.md`. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name).

## Inputs

- A GitHub issue: a number, `owner/repo#n`, or an issue URL. The same input on a ticket already in the store refreshes its mirror.
- An Azure DevOps work item: an id, or a work item URL. The same input on a ticket already in the store refreshes its mirror.
- A path to a spec or markdown file: its content is copied into the ticket and the path is recorded as `origin`.
- Pasted text or an idea: it becomes the ticket's description.
- No argument: offer a new ticket for the current branch's work, titled from the branch, and ask what the work is. The branch never identifies an existing ticket.

## Outputs

- A GitHub issue or Azure DevOps work item: its mirror under `raw/`, its journal entries upstream in `journal/`, and `ticket.json`, at the ticket directory `fetch` reports. Report its `ref`, where it is filed, its `type`, what the mirror holds (comments, journal entries written, relations, attachments, naming any attachment that did not download).
- Anything else: a new local ticket, `ticket.json` and `raw/ticket.md` at the paths `resolve --new` reported. Report its `ref`, its `type` and its directory.

## A GitHub issue

1. Turn the input into `fetch` arguments; `fetch` reads no URL. A number is `github:{n}`. `owner/repo#n` and an issue URL are `github:{n} --coordinate owner={owner} --coordinate repository={repo}`. A pull request URL is not a ticket: say so and stop.
2. Run `fetch <ref> [--coordinate ...]`, with `--context` when the session has one.
   - Exit 3: more than one product matches; ask which, and retry with its qualified reference.
   - The repository is bound nowhere: it cannot be filed. Ask the user to bind it with `/sdlc:setup`, or to name the namespace and product it belongs under; do not guess.
   - Any other error: report it as given and stop; nothing was written.
3. If `ticket.json` has no `type`, read the mirror (labels, title, body), decide `user-story`, `task`, `bug`, `spike` or `tech-debt`, say so and why, and add `type` to `ticket.json`, keeping every other key. A recorded `type` is never decided again unless the user asks to change it. The user can override at any time.

## An Azure DevOps work item

1. Turn the input into `fetch` arguments; `fetch` reads no URL. A bare id is `ado:{id}`. A URL `https://dev.azure.com/{organization}/{project}/_workitems/edit/{id}`, or the legacy `https://{organization}.visualstudio.com/{project}/_workitems/edit/{id}`, is `ado:{id} --coordinate organization={organization}`. Leave the project out: `fetch` reads the work item's team project upstream and files it under the product bound to it. A board, query or pull request URL is not a ticket: say so and stop.
2. Run `fetch` as above (exit 3 means more than one organization or product matches; ask which). It stops, with nothing written, when no organization is bound or the work item's team project is bound to no product: ask the user to bind it with `/sdlc:setup`; never guess an organization or project, and never file under `default`.
3. Decide and record the `type` once, as above, from the work item type, tags and content in the mirror.

## Invariants

- When the session has a context (`/sdlc:setup`), pass `--context {namespace}[/{product}]` to `resolve` and `fetch`, and tell the user where the ticket is filed.
- The mirror is a cache of the source, never authoritative; store nothing derived from the issue.
- The model decides the type once, says so, and the user can override it.
- Never write to GitHub or Azure DevOps.
- `fetch` mirrors the journal as `${CLAUDE_PLUGIN_ROOT}/shared/journal.md` "Mirrored entry" says; a journal file is never overwritten, so a refresh only adds entries.
- For a local ticket: ask once and write nothing before the yes; copy the content, since the ticket's file is its single source of truth; never overwrite an existing ticket.
