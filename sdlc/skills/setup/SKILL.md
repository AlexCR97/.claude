---
name: setup
description: Binds a ticket source (an Azure DevOps organization and project, a GitHub owner and repository) to a namespace and product, sets the defaults and scan roots, and sets, shows or clears the session context.
disable-model-invocation: true
argument-hint: "[what to set up]"
---

# Setup

Set up where tickets are filed and where they come from, as asked in `$ARGUMENTS` or by the user. You write the config files; `resolve` validates them on every call. There is no provider connection setup here: `az` and `gh` hold the credentials.

## Where config lives

Under the SDLC home (`~/.sdlc`, or `$SDLC_HOME`), one file per level; the inner level wins, objects merge key by key, anything else replaces, `[]` clears an inherited list.

| File                                 | Keys                                                                                                             |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `sdlc.json`                          | `default_namespace`, `default_source`, `scan_roots`, `protected_branches`, `sensitive`, `worktree_root`          |
| `{namespace}/namespace.json`         | `default_product`, `default_source`, `scan_roots`, `protected_branches`, `sensitive`, `worktree_root`, `sources` |
| `{namespace}/{product}/product.json` | `default_source`, `scan_roots`, `protected_branches`, `sensitive`, `worktree_root`, `sources`, `environments`    |

`worktree_root` is one absolute directory under which `implement` creates ticket worktrees instead of `{repository}/.worktrees/` (see `${CLAUDE_PLUGIN_ROOT}/shared/guard.md`).

`environments` is a product's list of environments, each `{"name": "qa", "production": false}`: names unique regardless of case, and `production` a boolean. `/sdlc:deploy` proposes it the first time it deploys the product and saves it on a yes; it is never set in `sdlc.json` or `namespace.json`.

`sensitive` is a list of hosts, databases or other targets a script must never touch unasked: the `effect` verb makes a script that names one ask first, even when it is read-only.

A binding is `sources.{source}.{coordinate}`. Each coordinate lives at the level its provider declares in `${CLAUDE_PLUGIN_ROOT}/shared/providers/{source}.json`: Azure DevOps `organization` in `namespace.json` and `project` in `product.json`; GitHub `owner` in `namespace.json` and `repository` in `product.json`. A namespace or product with no binding is valid: create its directory with a `{}` config file.

## Outputs

- A bind: the namespace's file holds the namespace-level coordinate, the product's file the product-level one. Keep the provider's own spelling (`Billing.App`) in the binding and derive the directory name as a lowercase slug (`billing-app`).
- Defaults and scan roots: set exactly what the user named; report anything inherited or defaulted.
- The session context: say `Session context: {namespace}[/{product}]`, or that it is cleared. It lives only in this conversation, never on disk. While it is set, pass `--context {namespace}[/{product}]` to every `resolve` call, and start your first output line with `Session context: ...`. Showing it also reports the effective config: run `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" resolve --new --title context --context <it>`, which creates nothing, and read `config` and `filing` from the output.

## Steps for a bind or a default

1. Read every config file you are about to change; if it exists, change only the keys asked for.
2. Write the files.
3. Run `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" resolve --new --title check` (`python3` where that is the interpreter's name). It creates nothing; a non-zero exit names the file at fault and why. Fix it and run it again.

## Invariants

- Never overwrite another level's file blindly: read it first and keep its other keys.
- Names are lowercase slugs.
- Nothing is bound twice: one namespace per organization or owner, one product per project or repository.
- The `default` namespace and every `default` product are fallbacks, never bound.
- Never write a credential into a config file.
