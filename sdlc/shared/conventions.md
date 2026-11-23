# Conventions

The rules the terms in [`GLOSSARY.md`](../GLOSSARY.md) carry. The glossary says what a thing is; this file says what must hold. Later formats (the plan, the journal, the guard policy) hold the rules specific to them.

## Filing and references

- **A ticket is filed under exactly one product. Filing organizes; coordinates identify.** Re-filing a ticket never changes where it lives upstream, and where it is filed is never written into the ticket: the directory is the record of that.
- **Namespace and product names are lowercase slugs.** `default` is reserved for the fallback products, and a name starting with `.` is never a namespace or a product. A provider's own spelling, such as `Billing.App`, belongs in a binding, never in a directory name.
- **Two products are never bound to the same coordinates**, or a pasted reference could be filed in two places. A fallback product is never bound at all: it holds what no binding fits.
- **The default product and the session context never file a ticket against its coordinates, and the default product never decides which existing ticket a reference means.** A wrong filing is visible and fixed by renaming the ticket directory; a wrong resolution attaches a session's work to the wrong ticket.
- **The session context never moves a ticket already filed.** It only prefers: which ticket a reference means, and where a new ticket goes.
- **A reference stored in a ticket is short within its own product and qualified across products**, because it is resolved from its own ticket's product first.

## Mirrors and local tickets

- **The source is the truth.** A mirror is a cache that a refresh may replace; no skill treats it as authoritative, and ticket content is never copied into a document derived from it.
- **A local ticket's ticket file is its own source of truth.** It is never refreshed from an adopted file's origin.
- **Nothing is filed by surprise.** Adoption asks once before it creates a local ticket (under the ship flag, invoking the ship run was the approval), and a branch name is never used to guess which existing ticket a session belongs to.

## Directories, paths and the workspace

- **A directory is the thing; a path is its name.** Say _directory_ for the location, and _path_ only for the string, stating what it is relative to. A `**Target:**` line holds a path, or two in a TDD phase: the test file, then the production file; the argument naming where code lives takes directories.
- **A plan has exactly one workspace**, recorded in the Workspace section of `plan.md`. The skills after `plan` work in that workspace; they do not rediscover it.
- **A workspace holds only the worktrees the work happens in**, one or several per repository. Worktrees of one repository can sit on different branches with different code, so each is listed on its own, and a worktree the workspace does not list is never read or changed.
- **The workspace excludes the SDLC home and every ticket directory.** Planning notes and artifacts are the ticket's record, not part of the code it changes, and neither is ever a scan root.
- **Scan roots differ in how far they are trusted.** A directory the user gave and the invocation directory are facts about this ticket: what they hold is in the workspace. A default scan root, or one found by search, says only where to look: what it holds is in the workspace when it matches the ticket.
- **Paths in `plan.md` are absolute in the Workspace section**, since that is how a later session finds the code. Everywhere else, a path is relative to its project's worktree or plain directory, and names that worktree or plain directory whenever the workspace holds more than one.

## Words that are not used

The `_Avoid_` lines of the glossary list the words to avoid. A retired word keeps its ordinary meaning where it names something else: the `git checkout` command, a network service to connect to, a user role such as an integrating service, a frontend UI component, a Python module, a C# or XML namespace, a MIME type, a ticket's _Component_ field, a directory literally named `repos`, the context a session has loaded.

A source's own vocabulary, such as the repository a GitHub source reads issues from and its `--repo` flag, or an Azure DevOps organization or project, belongs to that source's provider and never means a glossary term. In a binding it is a coordinate: never a namespace, a product or a project.

## Ship runs

Every skill but `setup` and `import` is model-invokable, so a ship run can invoke the others ([ADR 0007](../docs/adr/0007-skills-are-model-invokable-and-gate-themselves.md)). The developer's approval moves into each skill: one that writes outside the machine asks before it does, the only exception being `checkpoint` posting journal entries ([ADR 0009](../docs/adr/0009-a-remote-tickets-journal-lives-upstream.md)). What a ship run may do without asking is [ADR 0008](../docs/adr/0008-a-ship-run-may-commit-push-and-open-pull-requests.md)'s to decide; where this section and that ADR differ, the ADR wins.

- **The ship flag is the word `ship` standing alone among a skill's arguments**, never part of a reference, a quoted title or a pasted text. `/sdlc:ship` passes it to every skill it runs. A skill takes the flag off its arguments before reading the rest, and passes it on to any sdlc skill it invokes in turn.
- **Without the flag, every confirmation stands**, whoever invoked the skill: the user typing it, the model, or another skill.
- **Under the flag, a skill skips its confirmations.** Where it would ask for a yes, it shows what it is about to do and does it. Where it would ask the user to choose, it chooses on the evidence and says each choice in chat as a decision: what, why, and its cost if wrong. `checkpoint` carries those into the journal's Decisions, and the pull request body lists them.
- **Hard stops ask even under the flag**: merging into a protected branch, deploying to a production environment, and changing the upstream ticket's state. At one, show exactly what would happen and wait for an explicit yes; anything else is a no.
- **The flag waives questions, never refusals.** A guard refusal, a revision check that stops a write, a missing binding and a build that still fails stop the skill as they always do, and it reports them to the run. So does a question nothing in the run can answer, such as text the skill would have to invent: stop and report it rather than guess.
