---
name: deploy
description: Deploys an sdlc ticket's work to one of its product's environments (dev, QA, production) through a delegate skill, a project command or guided manual steps, and records the product's environments the first time. Use when asked to deploy, release or promote an sdlc ticket's work to a named environment.
argument-hint: "<environment> [<ticket reference>] [check] [ship]"
---

# Deploy

Deploy the work of a ticket to the environment `$ARGUMENTS` names. This is the lifecycle step after the pull request; a plan's `Deployment` phase is something else (it changes deployment files, through `implement`). Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). Branch rules are `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`; terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The environment**: a name, matched case-insensitively against the product's `environments`. Absent: list them and ask which.
- **The ticket**: a reference, else the ticket this session has been working on. `resolve <reference>` (with `--context {namespace}[/{product}]` when the session has one) reports its `product` and, in `config.environments`, the product's environments. Without a ticket, `resolve --new --title deploy` (with `--context`) reports the product the invocation directory or the session context files under; say which product it is. A ticket in a fallback product (`default`) has no product to deploy: say so, offer `/sdlc:setup` to bind one, and stop.
- **Sync** a ticket first: `sync <reference>` (with `--context`), reported as `${CLAUDE_PLUGIN_ROOT}/shared/sync.md` says, so `pulls.md` is current.
- **What to deploy**: the ticket's branch and its pull request from `pulls.md`, in the worktrees the plan's Workspace lists; else the invocation directory's repository and branch.
- **`check`**: the literal word. Settle the environments only, as Environments says, and deploy nothing; a product that already lists the environment needs nothing more. `/sdlc:ship` runs it before any work, so a missing environment is settled at the start of the run rather than at its end.
- **`ship`**: the [ship flag](../../shared/conventions.md#ship-runs). It waives the confirmation under Hard stops and confirmations, never the hard stops; the environments' yes, a manual step and a user-only delegate are waits it cannot waive.

## Environments

A product records its environments once, in its `product.json`, as `"environments": [{"name": "dev", "production": false}, ...]`. `resolve` validates the list on every call.

**The product has none, or lacks the one named.** Propose them, with or without `ship`:

1. Discover candidates in the product's repositories: CI workflows (`.github/workflows/`, `azure-pipelines*.yml`, `.gitlab-ci.yml`) and the environments they target, deployment files (per-environment values, overlays, Terraform workspaces, `docker-compose.*`), runbooks in a README or `docs/`, and project or installed skills that deploy (`.claude/skills/`, a skill named `deploy-*`).
2. Show one table: each environment's name, its production mark, and the file or skill that shows it. Mark an environment production when anything points that way (a name like `prod` or `live`, a GitHub environment with required reviewers, a promotion workflow that ends there) or when nothing settles it: a wrong mark of production costs one extra question, a wrong mark of not-production lets a deployment reach production unasked.
3. Ask for one yes: the hard stops depend on the production marks, so they are the user's call, and under `ship` this is a wait. On a correction, show the table again.
4. Save it as `/sdlc:setup` writes config: read `product.json`, set only `environments` (keeping every other key and every environment already listed), write it, then run `resolve --new --title check`. A non-zero exit names the problem; fix it and run it again. A saved list without the environment named: say which it lists and stop. Otherwise carry on with the deployment, or, under `check`, report the list and stop.

Change the list only when the user asks, through the same table and yes.

## Choosing how to deploy

Decide each run, from the installed skills and what the repository holds, and say the method and why in one line. The method most specific to this repository and environment wins:

- **A delegate**, chosen and run as [Delegates](../../shared/conventions.md#delegates) says: an installed skill whose description deploys this repository to this environment. Invoke it with the Skill tool and pass what it takes. An approval flag that waives the merge of a promotion pull request into a protected branch waives a hard stop, so it is never passed. A production deploy skill is often user-only: the user types it.
- **A project command**: a script, Make target, package script or workflow (`gh workflow run`) the repository provides for this environment. Run it after the yes or confirmation Hard stops and confirmations asks for.
- **Manual steps**: the deployment is a runbook or exists only in the user's head. Give one step at a time, exactly what to do and where, and wait for the user to say it is done before the next. A long procedure that captures values (secrets, dashboards) can become a script with `mattpocock-skills:wizard`; offer it.

## Hard stops and confirmations

- **A production environment** is a hard stop, with or without `ship`: show the environment, what is deployed (branch, commit, pull request) and the method, then wait for an explicit yes. Anything else (silence, "maybe", a question) is not one.
- **A merge into a protected branch** that the method requires (a release branch, a promotion pull request into a default branch) is a hard stop too, asked the same way. `guard protected --repo <directory>` lists what is protected. The merge goes through its pull request, by the delegate or the platform, after the yes; sdlc's own git commands never write to a protected branch.
- **Any other environment** is a confirmation: ask once before the first write outside the machine, showing the environment, what is deployed and the method. A delegate's own first confirmation is that question; do not ask it twice. Under `ship` it is waived ([ADR 0008](../../docs/adr/0008-a-ship-run-may-commit-push-and-open-pull-requests.md)).

## Report

The environment and whether it is production, the method, what was deployed (commit and pull request), the evidence that it landed (a green run, a new image tag, the user's word for a manual step), and any step left to the user. Say every decision as it is made: `checkpoint` builds its entry from this conversation.

## Invariants

- Environments live in `product.json` alone, and are saved only on a yes to the table shown.
- Nothing reaches a production environment, and nothing merges into a protected branch, without an explicit yes given for that deployment.
- A failed step stops the run: report its output, and change nothing to retry it differently. Rolling back is the user's call.
- Never read, print or store a credential; the tools the method uses hold them.
