# Connections

The policy for reaching an external system (a database, an API, a queue) from a session without the agent ever seeing its credentials, and the format of the files that make it possible. `/sdlc:connect` sets a connection up, `/sdlc:query` uses one, and the `connection` verb of `sdlc.py` does the mechanical part ([ADR 0010](../docs/adr/0010-connections-keep-the-runner-thin.md)). Terms are in [`GLOSSARY.md`](../GLOSSARY.md).

## What a connection is

A **connection** is a named, credentialed way to reach one external system in one environment. Its **profile** is one flat `.env` file, named after the profile, in the connections home: `~/.sdlc/.connections/`, or the directory `$SDLC_CONNECTIONS_HOME` names. The folder starts with a dot, so it is never a namespace and a whole-home export never includes it. It is copied between machines by hand.

- **Profile names** are lowercase letters, digits, `.`, `_` and `-`, starting with a letter or digit (`edx-qa`, `billing.dev`).
- **Values** are literals or `${VAR}`, which takes an earlier key of the same file first and then the process environment. A value is one line.
- **Reserved keys** describe the connection and are never passed to the command it runs:

| Key                     | Holds                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CONNECTION_KIND`       | Required. What the system is: `rest`, `generic`, or a name of your own. `connections/{kind}.md` holds the instructions for a kind this plugin ships. |
| `CONNECTION_PRODUCTION` | Optional `true` or `false`. Anything else counts as production and `connection check` names it.                                                   |
| `CONNECTION_ENV_FILE`   | Optional path to another env file, such as a project's `.env.qa`, whose keys join the profile's; the profile's own keys win. Relative to the profile's directory. |

A **registry** is optional: a namespace or product lists its connections by profile name under `connections` in its `namespace.json` or `product.json`, the inner level replacing the outer. An entry is `{"profile": "qa-db"}`, with an optional `"production": true` and, in a product file only, an optional `"environment"` naming one of that product's environments. It never holds a credential.

## The verb

Run as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection <action>`:

- `list [--context ns[/product]]`: every profile with its `kind`, `production`, `production_source` (`environment`, `registry`, `profile`, `name` or `default`), `environment`, `registered` and `file`. With `--context` it applies that context's registry and lists a registered profile that has no file here.
- `check`: validates every profile and prints key names only. It exits 1 when any has a problem, and warns about a value shorter than 4 characters, which is not masked.
- `run [--context ns[/product]] [--approved] [--dry-run] <profile> -- <command>`: runs the command with the profile's variables in its environment only, prints one JSON envelope (`exit_code`, `stdout`, `stderr`, `production`) with every value of 4 or more characters replaced by `***`, and exits 4 with a `reason` when it refuses. Options go before the profile. The command runs without a shell: to have `$VAR` expanded, wrap it in a shell (`sh -c '...'`, `pwsh -Command '...'`, or `python -c '...'` reading `os.environ`).

## Production

A connection is production by the first of these that applies:

1. The `production` mark of the product environment its registry entry links.
2. The registry entry's own `production` mark and the profile's `CONNECTION_PRODUCTION`, ranked together: either one saying production wins.
3. Its name, split on `-`, `_` and `.`: a `prod` or `production` segment makes it production, even beside a non-production one (`dev-prod-mirror`), except `pre` directly followed by `prod`, which is the one non-production term `pre-prod`. Otherwise `dev`, `development`, `int`, `integration`, `qa`, `test`, `uat`, `stage`, `staging`, `sandbox`, `local`, `localhost`, `preprod` or `pre` makes it non-production.
4. Anything else is production: a wrong mark of production costs one question, a wrong mark of not-production costs a production write.

## What may run without asking

The connection carries full credentials, so the gate is the environment and whether the command writes. The runner cannot tell whether an arbitrary command writes; that judgement is the model's, and a mistake costs data.

- **Read-only on a non-production connection:** run it unprompted when the task needs live data, and name the profile in the reply.
- **A write, on any connection:** show the exact command and wait for a yes, every time. A yes covers that one command. Inserts, updates, deletes, index or collection changes, `POST`, `PUT`, `PATCH` and `DELETE`, a restore or an import are writes; so is any command whose effect you cannot read from its text.
- **Production:** reach it only when the user's current message names that connection, and stay read-only unless that message also asks for the write. Pass `--approved` only then. Approval given earlier carries over to nothing.
- **A `sensitive` target** (the `sensitive` list of the effective config, as the `effect` verb reads it) is refused by `run` until `--approved`, and the user's yes is what approves it.
- **A refusal is final:** report its `reason` and ask; never look for another way to reach the same system.
- **A ship run** may use a connection only when its invocation or the ticket names it. A read-only call on a non-production connection runs unattended; any write, and any touch of a production connection, is a hard stop: checkpoint, send the notification and wait for an explicit yes ([Ship runs](conventions.md#ship-runs)). Nothing probes automatically after a deployment.

## Secrets

- **Never ask for a secret, read one or echo one.** Read only profile and key names, through `connection list` and `connection check`. Never open a profile, a `.env` file or the file `CONNECTION_ENV_FILE` names with a file tool or `cat`, never print a variable, and never put a value in a command line, a file, a commit or a reply.
- **A profile is written with placeholders**, or `${VAR}` references, and the user fills in the real values themselves.
- **Masking is a net, not a guarantee.** A value is masked only where it appears whole, and only when it is 4 or more characters; a transformed value (base64, URL-encoded, a hash of it) is not masked. Do not ask a tool to print a credential in any form.
- **Production profiles should hold read-only credentials.** That is the guard the runner cannot give: a command it cannot classify still cannot write.
- **Suggest permission entries and never edit `settings.json`.** A deny on reading `.env` files (`Read(**/.env*)`) and an ask on `connection run` for production profiles are the user's to add.

## Saving results

Query results are printed. They are saved under a ticket's `artifacts/` only when the user asks, named and kept as [`artifacts.md`](artifacts.md) says (append-only, `{name}.output.{ext}`), and never for a production connection: `/sdlc:export` zips whole ticket directories, so a saved result would leave the machine with the export. Say so in one line when saving.

## The always-loaded rule

A rule loads without any skill running, so the policy reaches a session that never invokes `/sdlc:query`. `/sdlc:connect` writes `~/.claude/rules/connections.md` from the block between the markers below, copied verbatim with `{SDLC_PY}` replaced by the absolute path of this plugin's `shared/sdlc.py`; it is regenerated, never edited by hand. It holds this machine's plugin path, so it is local to the machine, and a plugin update that moves the path is fixed by running `/sdlc:connect check`.

<!-- connections-rule:start -->
# Connections

Reach an external database, API or queue only through a connection profile, never with a credential of your own. The profiles live outside any project in the SDLC home's `.connections` folder.

- List them: `python "{SDLC_PY}" connection list` (add `--context <namespace>/<product>` inside a product). It prints names, kinds and production marks, never a value.
- Run one command with a profile's variables: `python "{SDLC_PY}" connection run <profile> -- <command>`. The variables reach the command's environment only, so wrap it in a shell (`sh -c '...'`) to expand `$VAR`. The output comes back masked.
- Read-only calls on a non-production profile run unprompted. Every write asks first, showing the exact command, and a yes covers that command only.
- A production profile is reached only when the user's current message names it, and stays read-only unless that message asks for the write; then pass `--approved`. An unrecognised profile name counts as production.
- Never ask for, read or print a secret. Do not open a profile or a `.env` file; `connection check` reports key names only.
- Never save a production result to a file. Never search for another way past a refusal.
- Setting one up, or checking them, is `/sdlc:connect`; asking a question of one is `/sdlc:query`. The full policy is in the sdlc plugin's `shared/connections.md`.
<!-- connections-rule:end -->
