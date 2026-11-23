---
name: ship
description: Ships an sdlc ticket through the whole cycle unattended (intake, plan, one commit per phase on a ticket branch, a ready pull request, and optionally a deployment), asking only at hard stops and steps only the user can take. Use only when asked to ship a ticket, spec or idea end to end.
argument-hint: "<ticket reference | spec file | \"text or idea\"> [pr | <environment>]"
---

# Ship

Run the work `$ARGUMENTS` names through the whole cycle in one go: intake, plan, then per phase implement, document, commit and checkpoint, a pull request, and a deployment when the end point is an environment. Ship is a sequencer: each step is another sdlc skill doing its own work by its own rules, and ship decides only the order, when to stop, and when to wait. Invoking it is the developer's approval for what [ADR 0008](../../docs/adr/0008-a-ship-run-may-commit-push-and-open-pull-requests.md) allows: one commit per phase on the ticket's own branch, pushing that branch, opening its pull request and marking it ready, and deploying to the end point when that environment is not production. Nothing else.

Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The flag, what it waives, decisions, the hard stops, the waits and the questions that stop a skill are [Ship runs](../../shared/conventions.md#ship-runs); branch rules are `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The work**: a ticket reference, or anything `/sdlc:intake` adopts: a spec file, text or an idea.
- **The end point**, one word after the work: `pr`, the default, ends at a ready pull request; any other word is an environment of the ticket's product, and the run ends with the work deployed there. After a reference or a file path, the next word is the end point; text has one only when it is quoted, so unquoted text is all work and ends at `pr`. Say the end point read as a decision.
- Pass `--context {namespace}[/{product}]` to `resolve` when the session has a context.

## Running the other skills

Invoke each sdlc skill with the Skill tool (`sdlc:intake`, `sdlc:plan` and so on), with the ticket's `ref` and `ship` among its arguments, and follow it to its end before the next step. Read its report: what it produced, every decision, and whether it stopped. A skill that stopped, on a refusal or a question the run cannot settle, ends the run through Failure.

- **Decisions.** Ship's own choices, such as the end point it read, are decisions as Ship runs says, like every skill's.
- **Waiting.** The run waits only where Ship runs says a skill still waits under the flag: a hard stop, or a step only the user can take. At every wait, each one and not only the first, and inside whichever skill reaches it, before asking: run `/sdlc:checkpoint <ref> ship`, so a run left waiting is on record, then send a push notification with the `PushNotification` tool (load it with ToolSearch, `select:PushNotification`, when it is deferred) naming the ticket and what waits. Where the tool is unavailable, say so in chat and wait all the same. A no at a hard stop ends the run there, with what it reached so far.

## Steps

1. **Take the work in.** Run `resolve <work>`. An existing local ticket needs no intake. Anything else goes through `/sdlc:intake <work> ship`, which mirrors or refreshes a remote ticket and adopts any other input as a local ticket. From here on, name the ticket by the `ref` that `resolve` or `intake` reported.
2. **Check the end point** before any work, from `product` and `config.environments` in `resolve <ref>`. `pr` needs nothing. An environment needs a product to deploy: a ticket in a fallback product (`default`) has none, so stop. A product that lists no environments, or none named this (case-insensitively): `/sdlc:deploy <environment> <ref> check ship` proposes the product's environments and waits for their one yes (a wait: checkpoint and notify first), then deploys nothing. A list saved without this environment ends the run: name those it lists. Say whether the end point is production: a production one means the run waits again before deploying.
3. **Plan.** `/sdlc:plan <ref> ship`. It settles the workspace and the seams itself and records each in the plan's Decisions. A ticket that already has a plan is reconciled, not replanned, so a run cut short carries on where it stopped.
4. **Check the delivery path** before the first edit, for each repository the Workspace lists that a phase not `Done` changes:
   - Its remote, `git -C <worktree> remote get-url origin`, is on GitHub or Azure Repos. Otherwise no pull request can be opened: stop.
   - Its worktree's branch is protected (`implement` then cuts the ticket branch and worktree), or is the ticket branch `guard.md` names for this ticket (reused). Any other branch: stop, since the run cannot tell that it is this ticket's, and a phase committed there lands on someone else's work.
5. **Run the phases**, each phase not `Done`, in order:
   1. `/sdlc:implement <ref> <phase> ship`. On the first phase it creates the ticket branch and worktree; on every phase it builds and tests, and runs `/sdlc:document` for the projects the phase changed. A phase still failing after one fix, or a `Blocked` phase: Failure.
   2. `/sdlc:commit <ref> <phase> ship`: one commit per repository the phase changed, the README edits included, pushed. A phase that changed nothing has nothing to commit: `commit` saying so is no failure, and the run goes on.
   3. `/sdlc:checkpoint <ref> ship`.
   4. After the first phase that committed anything: `/sdlc:pr <ref> ship`, which opens the pull request as a draft.

   A `Human Review` phase is the developer's: the run ends before it as Failure says, with the review it waits for as the failure, and the step left as it is.
6. **Mark it ready.** `/sdlc:pr <ref> ready ship`: the body rewritten from the net change, with every decision the run made, and the pull request marked ready. A run that committed nothing (a spike writes only under `artifacts/`) has no pull request: say where its finding is.
7. **Deploy**, when the end point is an environment: `/sdlc:deploy <environment> <ref> ship`. A production environment, or a merge into a protected branch that the deployment needs, is a hard stop, and a manual step or a user-only delegate is a wait: each waits as Waiting says.
8. **Checkpoint the end.** `/sdlc:checkpoint <ref> ship`, so the journal holds how the run ended. When `deploy` made decisions and the pull request is still open, run `/sdlc:pr <ref> ship` once more, so its body lists them too.

## Failure

A phase still failing after one fix attempt, or a skill that stopped, ends the run:

1. **The failing phase stays uncommitted** and its step `Blocked`, with the failure as its note, as `implement` left it. The failed fix is not retried a different way, and no test is changed to pass.
2. **Checkpoint**: `/sdlc:checkpoint <ref> ship`, so the entry records the failure, the `Blocked` step and the next action.
3. **The earlier phases are pushed**: `commit` pushed each as it committed. When one is not on the remote, that push failing is the failure to report.
4. **The pull request stays a draft that names the failure**: `/sdlc:pr <ref> ship <note>`, the note naming the phase, the step and the failure, without `ready`. A run that fails on its first phase has no commit and opens none; say so. A pull request already ready, as when `deploy` fails, stays ready: `pr` never moves one back, and the report names the failure.
5. **Report and end.** Once the developer has cleared the block and its status, `/sdlc:ship <ref> [end point]` again carries on from that phase.

## Report

- The ticket, the end point, and where the run ended: reached, or the phase, step and failure or hard stop it ended at.
- Per phase: its status, and each commit's short SHA and repository.
- The pull request: URL, and draft or ready.
- The deployment: the environment, whether it is production, and the evidence it landed; or that it was not reached.
- Every decision the run made, and that the journal and the pull request body hold them.
- What is left for the developer: the review, the merge (a hard stop), a block to clear.

## Invariants

- Ship does no work of its own on code, git or the ticket: every edit, commit, push, pull request, deployment and journal entry comes from the sdlc skill that owns it, run with `ship`.
- One ticket per run, on one ticket branch per repository, with one commit per phase per repository it changed.
- Never writes to a protected branch: the guard's refusals hold unchanged under `ship`, and a refusal ends the run.
- Never changes the upstream ticket's state: no closing, reopening, relabelling, reassigning or editing it. `checkpoint`'s journal comments are all the run posts on it.
- Nothing merges into a protected branch and nothing reaches a production environment without an explicit yes given at that hard stop.
- No co-author trailer naming Claude or any AI, in any commit or pull request.
