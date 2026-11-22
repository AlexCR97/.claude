# SDLC

A personal plugin that carries a unit of work from intake to documented code: a ticket is taken in, planned, implemented and recorded so another session can resume it. It works with tickets from GitHub and Azure DevOps and with local ones.

## Language

### Where tickets are kept

**SDLC home**:
The directory every ticket is stored under: `~/.sdlc`, or the directory `SDLC_HOME` names. It holds the root `sdlc.json` and one directory per namespace.
_Avoid_: Tickets home, ticket store, TICKETS_HOME

**Namespace**:
The top level of the SDLC home: one body of work that must never mix with another, such as an employer, a client or personal work. Holds products. Its `namespace.json` holds each source's namespace-level coordinate: an Azure DevOps organization, or a GitHub owner.
_Avoid_: Organization, owner, account

**Product**:
A body of work inside a namespace that tickets are filed under, such as a billing app or a notes app. Holds one directory per source. Its `product.json` holds each source's product-level coordinate: an Azure DevOps project, or a GitHub repository.
_Avoid_: Project, board, space

**Fallback product**:
A namespace's product named `default`, where a ticket is filed when its namespace is known but no product fits it. `default/default`, the fallback product of the namespace named `default`, receives a ticket that no namespace fits either.
_Avoid_: Catch-all, inbox

**Default namespace**:
The namespace a new ticket is filed under when neither the ticket nor the session context decides: the one `sdlc.json` names in `default_namespace`, else the namespace named `default`.

**Default product**:
The product a namespace files a new ticket under when nothing else decides: the one its `namespace.json` names in `default_product`, else its fallback product.

**Session context**:
The namespace, and optionally the product, a conversation chose with `/sdlc:setup`. It decides which ticket a reference means first and where a new ticket is filed; it changes nothing about a ticket already filed.
_Avoid_: Context (on its own), ticket-context

**Source**:
The system a ticket lives in: `github`, `ado` (Azure DevOps) or `local`.
_Avoid_: Provider (that names the files describing a source), tracker, backend

**Provider**:
The files that describe one source: what it can do, its coordinate names and id shape, how a ticket is downloaded from it, and its gotchas.
_Avoid_: Role file, contract, recipe

**Coordinates**:
The values that locate a ticket in its source, named by that source's provider: an organization and a project, an owner and a repository. A ticket's `ticket.json` records its own, and they win over any binding.
_Avoid_: Address, location

**Binding**:
The coordinates a namespace or product records for one source, under `sources.{source}` in its `namespace.json` or `product.json`. New tickets are downloaded with them, and a pasted address is filed by them.
_Avoid_: Mapping, ticket-setup

**Effective config**:
The `sdlc.json`, `namespace.json` and `product.json` that apply to a ticket, merged, the inner level winning. Every skill reads this, never one file alone.
_Avoid_: Settings, config.json

**Filing**:
Choosing the product a ticket not yet on disk is placed under: first which products can hold it, then which of them the session context, the invocation directory or the default product prefers.
_Avoid_: Routing, moving, ticket-move

**Ticket directory**:
One ticket's directory, at `{namespace}/{product}/{source}/{id}` in the SDLC home: `ticket.json`, `plan.md`, `journal/`, `pulls.md`, `raw/` and `artifacts/`.
_Avoid_: Ticket folder

**Qualified reference**:
`{namespace}/{product}/{source}:{id}`: names one ticket on the machine without ambiguity.
_Avoid_: Full reference, absolute reference

### Tickets and how they enter

**Ticket**:
One unit of work with a title, a description and acceptance criteria, identified by its source and id. Either remote or local.
_Avoid_: Issue, work item, task (a task is one ticket type)

**Remote ticket**:
A ticket whose source is GitHub or Azure DevOps. The source is the truth; the SDLC home holds a mirror of it.

**Local ticket**:
A ticket whose only home is the SDLC home. It has no mirror: its ticket file is the single source of truth.
_Avoid_: Note, draft

**Ticket file**:
The file `raw/ticket.md` of a local ticket, holding its title, description and acceptance criteria.
_Avoid_: Digest, ticket.md (on its own)

**Mirror**:
The non-authoritative, refreshable cache of a remote ticket in its `raw/` directory: its fields, comments, attachments, parent, blockers and labels as the source last reported them.
_Avoid_: Digest, snapshot, copy, ticket-fetch

**Revision**:
The marker a source gives for a ticket's current state, such as an Azure DevOps revision number or, where a source has none, a hash of its content. It is recorded when the ticket is mirrored, in `ticket.json` under the key `fingerprint`, and compared with the live one to learn that the ticket changed.
_Avoid_: Version, drift

**Intake**:
Bringing a ticket into the SDLC home: resolving its reference, filing it, mirroring a remote ticket or adopting a local one, and recording its type.
_Avoid_: Import, ticket-fetch, ticket-digest, ticket-create

**Adoption**:
Filing an input that is not yet a ticket, such as a spec file, pasted text or the current branch, as a local ticket by copying it in after one confirmation. An adopted file's original path is recorded as the ticket's origin and never refreshed.
_Avoid_: Conversion, import, ticket-create

**Ticket type**:
One of five kinds of work: user story, task, bug, spike, tech debt. Decided once at intake, recorded in `ticket.json`, and used by every later skill.
_Avoid_: Issue type, work item type, category

### The code a ticket touches

**Directory**:
A location on the machine that holds files. Every term in this section except _path_ is a kind of directory.
_Avoid_: Folder

**Path**:
The string naming a directory or a file. Always either absolute, or relative to a directory the text names.

**Scan root**:
A directory discovery starts from. Everything in a workspace is reachable from a scan root: beneath it, or by a reference followed out of it.
_Avoid_: Search root, base directory

**Default scan roots**:
The scan roots saved by `/sdlc:setup` in an `sdlc.json`, a `namespace.json` or a `product.json`. A plan starts from the effective list of the ticket's product: the nearest level that sets one.

**Invocation directory**:
The current directory when a skill ran.
_Avoid_: Working directory, cwd

**Repository**:
A local git repository. Named from its remote's URL, the last segment without `.git`; where it has no remote, from its main worktree's directory name.
_Avoid_: Repo

**Remote**:
A repository's hosted copy.
_Avoid_: Origin (that names the default remote, and an adopted ticket's origin is something else)

**Worktree**:
A working copy of a repository, with one branch checked out. Every repository has one main worktree and zero or more linked ones. Referred to by its repository's name, or as `{repository}@{branch}` where the workspace holds more than one worktree of that repository.
_Avoid_: Checkout, clone

**Plain directory**:
A directory in a workspace that is outside every repository. Referred to by its directory name.

**Project**:
A directory holding one unit that is built and changed together, detected by a build or deployment file. It lives in one worktree or plain directory, and it is where code changes happen.
_Avoid_: Service, application, module, component

**Workspace**:
Everything a ticket's code work happens in: its repositories with the worktrees the work happens in, its plain directories, and the projects inside them, plus the scan roots it was found from.
_Avoid_: Environment, sandbox

### Planning the work

**Plan**:
The ticket directory's `plan.md`: the confirmed workspace and the work as phases of steps, with each step's status. One plan per ticket.
_Avoid_: Implementation plan, plan file, digest

**Phase**:
A part of a plan with one activity, a scope and the projects it touches. Its status is derived from its steps.
_Avoid_: Stage, milestone

**Step**:
The smallest unit of a plan: one change to one target, with a status.
_Avoid_: Task, subtask

**Activity**:
What a phase does: `TDD`, `Development`, `Testing`, `Design`, `Deployment`, `Documentation` or `Human Review`.
_Avoid_: Kind, category

**Step status**:
Where a step stands: `Pending`, `In Progress`, `Blocked` or `Done`. The honest record of progress that `plan`, `implement` and `checkpoint` share.
_Avoid_: State

### Branches and worktrees

**Default branch**:
The branch a repository's `origin/HEAD` names, usually `main`.
_Avoid_: Trunk, master

**Protected branch**:
The default branch, plus any branch matching a pattern in `protected_branches` in the effective config.
_Avoid_: Locked branch

**Ticket branch**:
A branch created for one ticket's implementation, cut from `origin/{default branch}` and named from the ticket's type and id.
_Avoid_: Feature branch

**Ticket worktree**:
The linked worktree holding a ticket branch.

### Test-driven development

**TDD phase**:
A plan phase whose activity is `TDD`: its behaviour is written test-first, one slice per step.

**Seam**:
The public boundary a test exercises: a public method, an endpoint, a command handler, a component's rendered output. Behaviour is observed there without reaching inside.
_Avoid_: Test boundary, hook

**Slice**:
One test at one seam plus the least production code that makes it pass. Each step of a TDD phase is one slice, a tracer bullet the next slice builds on.
_Avoid_: Increment, task

**Red**:
A slice's test run before its production code exists, failing on the missing behaviour itself.
_Avoid_: Failing test (a test can fail for the wrong reason)

**Green**:
The same test passing after the least production code that satisfies it.

**Test project**:
A project that holds tests and a runner able to execute them against another project.

**Test-setup phase**:
A `Testing` phase that creates the test project a TDD phase needs, where none can exercise its code yet.

### Research and running scripts

**Artifact**:
A file a run produces that is not a change to the workspace: a probe, its captured output, or a note of what was found. Kept under the ticket directory's `artifacts/`, as a record of how the ticket was investigated, never as a deliverable.
_Avoid_: Output, attachment, deliverable

**Probe**:
A small script written to learn a fact by running it, such as how many rows a table holds, rather than by reading. Its output is an artifact.
_Avoid_: Spike (that names a ticket type), experiment

**Effect**:
What a script does to the world: `read-only`, or `writes`. A script declares it in its header, and the `effect` verb checks the declaration against the code before the script may run without asking.
_Avoid_: Side effect, permission

### Recording a session

**Journal**:
The ticket directory's `journal/`: one entry per file, each named by its UTC timestamp so the files sort by time.
_Avoid_: Log, journal.md

**Journal entry**:
One session's self-contained account of itself, carrying forward whatever is still open. The latest is the one a resume reads.
_Avoid_: Checkpoint (that names the act of writing one), note

**Pull request record**:
The ticket directory's `pulls.md`: one link to each pull request that delivers the ticket's work, each with the status it had when the record was last refreshed, and the time of that refresh.
_Avoid_: PR list

**Checkpoint**:
The act of recording a session on a ticket: writing a new journal entry, correcting the plan's stale step statuses and refreshing the pull request record. Run by `/sdlc:checkpoint`.
_Avoid_: Save, snapshot

**Canonical URL**:
A ticket's address in its source's preferred form. A ticket pasted under another form of its address is recorded under this one.
