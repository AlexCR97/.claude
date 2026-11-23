# PowerShell profile context switchers

The user's PowerShell 7 profile ([github.com/AlexCR97/PowerShell](https://github.com/AlexCR97/PowerShell)) defines functions that point a CLI at an environment: `Connect-Mongo` and `Invoke-MongoScript` for `mongosh`, `Use-Temporal` for the `temporal` CLI, and `Use-KubeContext` for `kubectl`. Use them whenever a task needs one of these tools against a real environment. The profile's `README.md` documents their parameters and profile files.

## When this applies

Only on a machine whose profile folder, `Split-Path $PROFILE`, holds `Mongo.ps1` or `Use-Temporal.ps1`. Elsewhere, ignore this file.

Each switcher reads its profiles from a gitignored `*.local.json` in that folder, which the user copies between machines by hand. When the file a task needs is missing, tell the user and stop there; the user creates it.

## Calling the functions

The PowerShell tool starts without the profile and keeps nothing between calls: environment variables, functions and background jobs end with the call. So every call that uses a switcher:

- starts with `. $PROFILE;`
- switches and runs its commands within that one call;
- names the profile explicitly, since `Connect-Mongo` without one opens a menu that the non-interactive shell cannot answer.

```powershell
. $PROFILE; Use-Temporal edgraph-dev; temporal workflow list --limit 5
. $PROFILE; Connect-Mongo edx-int -Database edx --quiet --eval "db.getCollectionNames()"
. $PROFILE; Invoke-MongoScript .\query.js edx-int
```

- **Profile names** are the top-level keys of `Mongo.local.json` and `Use-Temporal.local.json`: `(Get-Content -Raw $file | ConvertFrom-Json).PSObject.Properties.Name`.
- **`mongosh` arguments** take their `--long` form. PowerShell binds a short flag such as `-e` to its own parameters.
- **Temporal `edx-*` profiles** open an EKS port-forward that takes up to 20 seconds and closes with the call, so batch related `temporal` commands into one call.
- **A failed port-forward** usually means expired AWS credentials. Its error names the AWS profile; suggest the user run `! aws sso login --profile <that profile>`.
- **`kubectl`** gets `--context` and `-n` on every command. `Use-KubeContext` prompts with `Read-Host` and switches the kubeconfig of every shell the user has open, so leave it, `kubectl config use-context` and `kubectl config set-context` to the user.

## What may run without asking

These connections carry full-admin credentials, so the gate is the environment and whether the command writes.

- **Read-only, non-production:** run it unprompted when the task needs live data, and name the profile in the reply.
- **Writes, non-production:** show the exact command and wait for a yes, every time. A yes covers that one command. Writes include Mongo inserts, updates, deletes and index or collection changes; Temporal signal, cancel, terminate, reset and schedule changes; and `kubectl` apply, delete, edit, scale, patch and rollout.
- **Production:** `edx-prod`, `edgraph-prod-usc` and the `edx-eks-production-eus1` context. `edx-preprod` is not production. Treat any new profile or context named `prod` or `production`, other than `preprod`, as production. Reach production only when the user's current message names it, and stay read-only unless that message also asks for the write.

## Secrets

`*.local.json` holds connection strings with passwords and Temporal API keys. Read only its top-level profile names, leave the file unedited, and keep connection strings and `$env:TEMPORAL_API_KEY` out of commands' printed output and replies.
