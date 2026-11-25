# PowerShell profile context switchers

The user's PowerShell 7 profile defines functions that point a CLI at an environment: `Connect-Mongo` and `Invoke-MongoScript` for `mongosh`, `Save-MongoDump`, `Restore-MongoDump` and `Import-MongoExport` for the database tools (`mongodump`, `mongorestore`, `mongoimport`), `Use-Temporal` for the `temporal` CLI, and `Use-KubeContext` for `kubectl`. Use them whenever a task needs one of these tools against a real environment. The profile's `README.md` documents their parameters and profile files.

## When this applies

Only on a machine whose profile folder, `Split-Path $PROFILE`, holds `Mongo.ps1` or `Use-Temporal.ps1`. Elsewhere, ignore this file.

Each switcher reads its profiles from a gitignored `*.local.json` in that folder, which the user copies between machines by hand. When the file a task needs is missing, tell the user and stop there; the user creates it.

## Calling the functions

The PowerShell tool starts without the profile and keeps nothing between calls: environment variables, functions and background jobs end with the call. So every call that uses a switcher:

- starts with `. $PROFILE;`
- switches and runs its commands within that one call;
- names the profile explicitly, since `Connect-Mongo` without one opens a menu that the non-interactive shell cannot answer.

```powershell
. $PROFILE; Use-Temporal <profile>; temporal workflow list --limit 5
. $PROFILE; Connect-Mongo <profile> -Database <database> --quiet --eval "db.getCollectionNames()"
. $PROFILE; Invoke-MongoScript .\query.js <profile>
. $PROFILE; Save-MongoDump <profile> -Label preMigration
. $PROFILE; Restore-MongoDump <dump folder> <profile> -Drop -WhatIf
```

- **Profile names** are the top-level keys of `Mongo.local.json` and `Use-Temporal.local.json`: `(Get-Content -Raw $file | ConvertFrom-Json).PSObject.Properties.Name`. List them before the first call that needs one.
- **`mongosh` arguments** take their `--long` form. PowerShell binds a short flag such as `-e` to its own parameters.
- **Dumps** go to `.mongo/dumps/<profile>/<yyyy-MM-dd_HHmmss>[_label]/<database>` under the current directory. `Restore-MongoDump` and `Import-MongoExport` take such a folder as a mandatory path. The database is `-Database`, then the profile's `database`, then the default in `Mongo.ps1`. `-Drop` is off by default.
- **Restore and import confirm**, and the non-interactive shell cannot answer the prompt. Preview with `-WhatIf`, show the user the exact command, and add `-Confirm:$false` only to the call the user said yes to.
- **A missing `localhost` profile** is the usual reason a local restore or import stops. The user adds it to `Mongo.local.json` on each machine; tell them and stop.
- **Temporal profiles that target an EKS cluster** open a port-forward that takes up to 20 seconds and closes with the call, so batch related `temporal` commands into one call.
- **A failed port-forward** usually means expired AWS credentials. Its error names the AWS profile; suggest the user run `! aws sso login --profile <that profile>`.
- **`kubectl`** gets `--context` and `-n` on every command. `Use-KubeContext` prompts with `Read-Host` and switches the kubeconfig of every shell the user has open, so leave it, `kubectl config use-context` and `kubectl config set-context` to the user.

## Production or not

Classify every Mongo profile, Temporal profile and `kubectl` context by its real name, case-insensitively, split into segments on `-`, `_` and `.`:

- **Production:** any segment is `prod` or `production`, even beside a non-prod term (`dev-prod-mirror`). `preprod` and `pre-prod` are one non-prod term, so they do not count.
- **Non-production:** no production segment, and at least one segment is `dev`, `development`, `int`, `integration`, `qa`, `test`, `uat`, `stage`, `staging`, `sandbox`, `local`, `localhost`, `preprod`, `pre-prod` or `pre` as a whole segment, or an obvious synonym of one.
- **Anything else is production.** An unrecognised name gets the production rules.

## What may run without asking

These connections carry full-admin credentials, so the gate is the environment and whether the command writes.

- **Read-only, non-production:** run it unprompted when the task needs live data, and name the profile in the reply. `Save-MongoDump` counts as read-only, since it changes nothing on the server and writes only under `.mongo/`.
- **Writes, non-production:** show the exact command and wait for a yes, every time. A yes covers that one command. Writes include Mongo inserts, updates, deletes and index or collection changes, and every `Restore-MongoDump` and `Import-MongoExport`; Temporal signal, cancel, terminate, reset and schedule changes; and `kubectl` apply, delete, edit, scale, patch and rollout.
- **Production:** reach it only when the user's current message names it, and stay read-only unless that message also asks for the write. `Restore-MongoDump` and `Import-MongoExport` refuse a profile named `prod` or `production` whatever the message says; never work around the refusal. `Save-MongoDump` may dump production when the message names it.

## Secrets

`*.local.json` holds connection strings with passwords and Temporal API keys. Read only its top-level profile names, leave the file unedited, and keep connection strings and `$env:TEMPORAL_API_KEY` out of commands' printed output and replies.
