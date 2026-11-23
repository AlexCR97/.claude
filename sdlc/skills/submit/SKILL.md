---
name: submit
description: Creates one GitHub issue or Azure DevOps work item upstream, or edits one (title, description, acceptance criteria, state, labels or tags), showing exactly what it writes first. Use when asked to submit, file or edit one issue or work item with sdlc, or to file a to-spec or to-tickets body on Azure DevOps.
argument-hint: "[<ticket reference>] [what to create or change] [ship]"
---

# Submit

Write one ticket to its source, from `$ARGUMENTS` and the conversation. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name); `gh` and `az` write upstream, and the source's gotchas are in `${CLAUDE_PLUGIN_ROOT}/shared/providers/{github,ado}.md`, read the one you need. Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- A ticket reference (a number, `owner/repo#n`, an Azure DevOps id or a URL; turn it into `fetch` arguments as `${CLAUDE_PLUGIN_ROOT}/skills/intake/SKILL.md` does) and what to change: an **edit**.
- No reference: a **create**. The content is the user's words, a to-spec or to-tickets body in the conversation, or a file they name. Its title is the user's, else the file's first `#` heading; ask when there is none.
- Exactly one ticket. A to-tickets set, or any request for several, is not offered: say so and ask which one to write now.

## Edit

1. `resolve <reference>` (with `--context {namespace}[/{product}]` when the session has one). A ticket not in the store: offer `/sdlc:intake <reference>` and stop. A local ticket has no upstream: say so and stop.
2. **Revision check.** `fetch <reference> --check` (with `--context`). `unchanged`, `journal_only` or `journal_unmirrored` continues: nothing but journal entries moved since the mirror, so a checkpoint never blocks an edit. `changed`, `never_mirrored` or `stale_mirror` stops the write (a stale mirror needs only the refresh): read the live ticket (`gh api`, `az rest`; reads only), say what changed against the mirror, and offer `/sdlc:intake <reference>` to refresh. An error stops it too.
3. Build the change from the mirror (`raw/raw.json`). Where a field is one combined value (labels, tags, a body holding several sections), build its new value from the whole of its current one, so nothing unnamed is lost. Never invent text; ask for it.
4. Show a before and after of every field that changes, exactly as it will be written. Nothing would change: say so and stop.
5. Ask for a yes. Anything else (silence, "maybe", a question) is not one; on a no, send nothing. Under the [ship flag](../../shared/conventions.md#ship-runs) go on without asking, unless the change sets the ticket's state: that is a hard stop, and waits for a yes even then.
6. Before writing, run the revision check again, since time has passed; any status but the three step 2 continues on stops the write as there. Otherwise write as the provider notes say. On Azure DevOps the patch opens with the `test /rev` guard, on this check's `live` revision.
7. **Fetch it back**: `fetch <reference>` so the mirror is what is now upstream. Say what each field now holds against what was confirmed. The plan, if there is one, was built from the old content: say so.

## Create

1. **Where.** The target is the source's binding, never a guess. With a session context, `resolve --new --title "<title>" --context {namespace}[/{product}]` creates nothing and reports `config.sources`: the owner and repository, or the organization and project, bound there. Both sources bound: ask which. Without a context, ask the user for the repository or project, then probe it: `resolve {source}:1 --coordinate {name}={value} ...` (read-only) must file under a bound product, not a `default` one. Not bound: ask the user to run `/sdlc:setup`, and stop; a ticket the store could not mirror is not created.
2. Assemble title, body and the labels or tags the user named, and on Azure DevOps its work item type, chosen as the provider notes say. Pass a to-spec or to-tickets body through exactly as written: its sections (Problem Statement, Parent, What to build, Acceptance criteria, Blocked by ...) stay as they are and are not rewritten. A Parent or Blocked by section stays text; this skill links nothing.
3. Show the full proposal: the source and where (owner/repository or organization/project), the title, labels or tags, and the whole body. Azure DevOps prose is HTML: show the converted HTML and say the Markdown was converted. Ask for a yes as above; under the ship flag, go on without asking.
4. Create it. The new reference (issue number, work item id) is in the response.
5. **Fetch it back**: `fetch {source}:{id}` with the `--coordinate` values the create used (and `--context`), so it is filed and mirrored. Then decide and record its `type` once, exactly as intake does for a fetched ticket (its step 3 on a GitHub issue); the type is not written upstream.
6. Report the reference, the upstream URL and where it is filed.

## Invariants

- Nothing is sent upstream before an explicit yes to the exact content shown, or, under the ship flag, before that content is shown. A state change always waits for the yes. A change to the content needs a new preview and, without the flag, a new yes.
- No edit goes out over a ticket whose content moved since it was mirrored: the revision check stops it; no way around it is offered. A journal entry is not content.
- Write only what was asked: no state change, close, label, tag, assignee, milestone or comment nobody named, and no triage label added by habit.
- The target repository or project is the product's binding or the user's own word, checked against the bindings. Unbound: `/sdlc:setup`.
- A ticket written upstream is always fetched back; the local files are never edited to imitate the write.
- Scratch files (a body, a patch, a live read) go in the system temp directory, never the working tree or the ticket directory, and are deleted afterwards.
- Never read, print or store a token; `gh` and `az` hold the sign-in. A failed write is reported as given, and nothing is retried with a changed revision.
