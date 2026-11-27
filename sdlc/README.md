# sdlc

Agentic software development life cycle: intake, plan, implement and document. A Claude Code plugin that mirrors a GitHub issue or an Azure DevOps work item (or adopts a spec, text or an idea) into a local store, then plans, implements, checkpoints and documents it, keeping what a later session needs on disk.

Every skill but `/sdlc:setup` and `/sdlc:import` is model-invokable ([ADR 0007](docs/adr/0007-skills-are-model-invokable-and-gate-themselves.md)): the model may run one when its description fits the request, and one sdlc skill may run another. Each description says narrowly when its skill applies, and a skill that writes outside the machine asks before it does. `setup` and `import` rewrite the SDLC home, so they stay explicit-only (`disable-model-invocation: true`) and run only when you type them. A ship run passes the `ship` flag, which waives every confirmation but the hard stops and the steps only you can take; [shared/conventions.md](shared/conventions.md#ship-runs) has the rules.

## Skills

| Skill              | Takes                                                                                                                                    | Produces                                                                                                                                                             |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/sdlc:setup`      | A source to bind (an Azure DevOps organization and project, a GitHub owner and repository), defaults, scan roots, or the session context | The config files under the SDLC home; once per binding                                                                                                               |
| `/sdlc:intake`     | A GitHub issue, an Azure DevOps work item, a spec file, pasted text or an idea, or nothing (the current branch's work)                   | A ticket: the upstream mirror under `raw/` and its journal in `journal/`, or a local ticket, plus `ticket.json`                                                      |
| `/sdlc:plan`       | A ticket reference, or a non-ticket input, and optionally directories                                                                    | `plan.md`: phased, file-level, with test-first phases where a seam allows; re-run to update step status                                                              |
| `/sdlc:implement`  | A ticket and the phases to run (`all`, or a list)                                                                                        | Code changes, built and tested; step status kept in `plan.md`. Never touches a protected branch, never commits unasked                                               |
| `/sdlc:checkpoint` | A ticket and an optional note                                                                                                            | A journal entry (where the code is, what was done and decided, what blocks, the next action), posted as a comment on a remote ticket, and the pull request record    |
| `/sdlc:resume`     | A ticket                                                                                                                                 | One briefing ending in the single next action, including what changed upstream; writes only the sync of its mirror and pull request record                           |
| `/sdlc:submit`     | One ticket to create or edit upstream, with a to-spec or to-tickets body if you have one                                                 | A GitHub issue or Azure DevOps work item, written only after a preview and an explicit yes                                                                           |
| `/sdlc:document`   | A ticket and phase, paths, or `all`                                                                                                      | Edits to the README of each project the change touched; never commits                                                                                                |
| `/sdlc:commit`     | Optionally a ticket and its phase, and `push`                                                                                            | The phase's or session's changes committed per repository, linking the ticket when there is one; asks first unless shipping                                          |
| `/sdlc:pr`         | Optionally a ticket, and `ready` to mark its pull request ready for review                                                               | A draft pull request per repository the work changed, linking the ticket when there is one; ready on `ready`; and the pull request record                            |
| `/sdlc:deploy`     | An environment, and optionally a ticket                                                                                                  | The work deployed by a delegate skill, a project command or manual steps; the environments saved on first use after a yes; production always asks                    |
| `/sdlc:ship`       | A ticket reference, or a spec file, text or an idea, and an end point (`pr`, the default, or an environment)                             | The whole cycle in one unattended run: a ticket branch with one commit per phase, a ready pull request, a deployment to the end point; waits only where you must act |
| `/sdlc:export`     | Nothing (the whole SDLC home), a namespace, `{namespace}/{product}` or a ticket reference, and optionally where to write it              | An archive: a zip of that scope's directories, the config files above it and a manifest, for `/sdlc:import` on another machine                                       |
| `/sdlc:import`     | An archive `/sdlc:export` wrote                                                                                                          | The archive merged into the SDLC home after a report and a yes: missing files added, conflicts asked per ticket, nothing deleted                                     |

## The cycle

```mermaid
flowchart TD
    subgraph Plan["Think (companion plugins)"]
        G["grill-me / grill-with-docs / brainstorming"] --> S["to-spec"]
        S --> T["to-tickets"]
    end
    T -->|"GitHub issues"| I
    S -->|"or one ticket at a time"| SUB["/sdlc:submit (Azure DevOps)"]
    SUB --> I
    SETUP["/sdlc:setup (once per binding)"] -.-> I
    SHIP["/sdlc:ship (every step below in one run; waits only where you must act)"] -.-> I
    I["/sdlc:intake"] --> P["/sdlc:plan"]
    P --> M["/sdlc:implement"]
    M --> D["/sdlc:document (offered after each phase)"]
    D --> CM["/sdlc:commit"]
    CM --> C["/sdlc:checkpoint"]
    C -->|"next phase"| M
    C --> PR["/sdlc:pr (draft, then ready)"]
    PR -.->|"to an environment"| DEP["/sdlc:deploy"]
    C -.->|"new session"| R["/sdlc:resume"]
    R --> M
    C -.-> H["handoff"]
```

1. **Think.** Sharpen the idea with `mattpocock-skills:grill-me`, `mattpocock-skills:grill-with-docs` and/or `superpowers:brainstorming`. Turn the result into a spec with `mattpocock-skills:to-spec`, then into tickets with `mattpocock-skills:to-tickets`.
2. **File.** `to-tickets` publishes to GitHub itself. For Azure DevOps, or to create or change a single ticket, use `/sdlc:submit`, one ticket at a time.
3. **Intake, plan, implement.** `/sdlc:intake`, then `/sdlc:plan`, then `/sdlc:implement`. `implement` offers `/sdlc:document` after each phase.
4. **Deliver.** `/sdlc:commit` commits a phase, `/sdlc:pr` opens its pull request as a draft and `/sdlc:pr ready` marks it ready, and `/sdlc:deploy <environment>` deploys it. Each asks before it writes outside the machine.
5. **Or ship it.** `/sdlc:ship <ticket> [pr | <environment>]` runs steps 3 and 4 unattended: intake, a plan whose open choices it decides itself, one ticket branch, and per phase implement, document, commit and checkpoint, then a ready pull request and the deployment to the end point. It waits only at a hard stop or a step only you can take (saving a product's environments, a manual deployment step, a skill only you may type), and at each it checkpoints, sends a push notification and waits for you. Every decision it made is in the journal, and the ones about the code are in the pull request body. A phase still failing after one fix ends the run: that phase stays uncommitted and `Blocked`, the earlier ones are pushed, and the pull request stays a draft naming the failure ([ADR 0008](docs/adr/0008-a-ship-run-may-commit-push-and-open-pull-requests.md)).
6. **Stop and come back.** `/sdlc:checkpoint` before attention leaves the ticket; `/sdlc:resume` first thing in a fresh session. On a remote ticket, checkpoint also posts the journal entry as a comment on the issue or work item, always, and nothing else goes upstream ([ADR 0009](docs/adr/0009-a-remote-tickets-journal-lives-upstream.md)). `/sdlc:resume` on another machine mirrors those entries back as it syncs, so it starts from the latest. `mattpocock-skills:handoff` compacts a conversation for another agent when a journal entry is not what you need.
7. **Once per binding.** `/sdlc:setup` binds a repository or project to a namespace and product, so `intake` can file what it mirrors.

## How work enters the cycle

- **A to-tickets or to-spec issue on GitHub:** `/sdlc:intake 1234`, `/sdlc:intake acme/billing-app#1234` or the issue URL. Its repository must be bound by `/sdlc:setup`. The same input again refreshes the mirror.
- **An Azure DevOps work item:** `/sdlc:intake 1234` or its URL, with its team project bound.
- **A spec file, pasted text or an idea:** `/sdlc:intake docs/spec.md` or `/sdlc:intake "retry failed invoice exports"`. It becomes a local ticket after one confirmation showing its reference, type and directory; a file's path is kept as `origin`.
- **The current branch:** `/sdlc:intake` with no argument offers a local ticket titled from the branch and asks what the work is. A branch never identifies an existing ticket.
- **Adoption in any skill:** `plan`, `implement`, `checkpoint` and `resume` accept the same non-ticket inputs and adopt them first, as [shared/adoption.md](shared/adoption.md) says.

## Install

```bash
claude plugin marketplace add AlexCR97/.claude
claude plugin install sdlc@alexcr97
```

The marketplace is `alexcr97` ([.claude-plugin/marketplace.json](../.claude-plugin/marketplace.json)) and the plugin is `sdlc`. The scripts need Python as `python` or `python3`, plus `git`, and `gh` or `az` for the sources you use; both CLIs hold the credentials.

## Develop

Load the plugin from a checkout, without installing it:

```bash
claude --plugin-dir path/to/sdlc
claude plugin validate path/to/sdlc
```

Run the tests from the repository root:

```bash
uvx --python 3.14 --with pytest pytest sdlc/tests -q
```

Tests run the `sdlc.py` command line against a scratch `SDLC_HOME`, with `gh` and `az` replaced by launcher stubs; nothing reaches the network.

## Data

Everything lives under the SDLC home, `~/.sdlc` or `$SDLC_HOME`:

```
{namespace}/{product}/{source}/{id}/
    ticket.json  raw/  plan.md  journal/  artifacts/  pulls.md
```

| File                                 | Level       | Holds                                                                                                        |
| ------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------ |
| `sdlc.json`                          | the home    | `default_namespace`, `default_source`, `scan_roots`, `protected_branches`, `sensitive`, `worktree_root`      |
| `{namespace}/namespace.json`         | a namespace | the same keys (`default_product` instead of `default_namespace`), and the namespace-level source coordinates |
| `{namespace}/{product}/product.json` | a product   | the same keys, the product-level source coordinates, and `environments` (each a name and a production mark)  |
| `…/{id}/ticket.json`                 | a ticket    | its record, keyed as [shared/store.md](shared/store.md) lists                                                |

Credential profiles for connections sit beside the tickets in `.connections/` (or the directory `$SDLC_CONNECTIONS_HOME` names), one flat `.env` file per profile. The folder starts with a dot, so it is never a namespace and a whole-home export never includes it. A `namespace.json` or `product.json` may also list its connections by profile name under `connections`: each entry can mark a profile production, and an entry in a product file can link one of that product's environments. An entry never holds a credential, and a product's list replaces its namespace's.

The inner level wins. [GLOSSARY.md](GLOSSARY.md) defines the terms, [shared/conventions.md](shared/conventions.md) the filing, mirror, path and ship-run rules, and `/sdlc:setup` the keys. Specific formats sit beside it in [shared/](shared/): [store.md](shared/store.md) (the layout and `ticket.json`), [archive.md](shared/archive.md) (the archive and its manifest), [plan.md](shared/plan.md), [journal.md](shared/journal.md), [sync.md](shared/sync.md), [artifacts.md](shared/artifacts.md), [guard.md](shared/guard.md), [tdd.md](shared/tdd.md) and [types.md](shared/types.md).

## Scripts

Skills call `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>`. There are seven verbs, each for work that must come out identical every time:

- `resolve`: report the ticket directory for a reference, or where a new ticket would be filed; read-only.
- `fetch`: mirror an issue or work item into `raw/`, and its journal entries into `journal/`; `--check` compares revisions without writing, and says when only journal entries moved.
- `sync`: refresh a ticket's mirror when it changed upstream beyond this machine's journal posts, and rewrite its pull request record from the plan's Workspace branches; which skills run it, and when, is in [shared/sync.md](shared/sync.md).
- `guard`: answer whether an operation on a repository or branch is allowed under the protected-branch policy.
- `effect`: vet a script's side effects (including a `sensitive` target) before it runs.
- `archive export`: write the SDLC home, or one namespace, product or ticket of it, to a zip with a manifest; never writes inside the home.
- `archive import`: report, as JSON, what merging an archive into the home would add, merge and ask about; with `--apply`, the digest and a choice per conflicting ticket, write that merge.

- `connection list`: list the connection profiles with their kind and production mark, and with `--context` apply that context's `connections` registry (a linked environment's mark wins); `connection check` validates each profile, and exits 1 when any has a problem. Both report names only, never a value.

[ADR 0006](docs/adr/0006-scripts-and-instructions-are-for-mechanical-work-only.md) explains why there are so few.
