---
name: connect
description: Sets up a connection to an external database or API as a credential profile the model never reads, or checks the existing ones, and keeps the always-loaded rule that carries the policy. Use when asked to connect a new data source or API, add a connection profile, or check the connections, with sdlc.
disable-model-invocation: true
argument-hint: "new [<system>] | check"
---

# Connect

Set up or check a connection as `$ARGUMENTS` asks. A connection is a credential profile that `/sdlc:query` and the `connection` verb use without the model ever seeing a secret. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The policy, the profile format and the verb are `${CLAUDE_PLUGIN_ROOT}/shared/connections.md`; read it before anything else. Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

This skill is explicit-only (`disable-model-invocation`): it writes credential files and a global rule, so it runs only when the developer types it.

## Inputs

- **`new [<system>]`**: set up one connection. The system, if named, is what it reaches (`billing database`, `Stripe API`).
- **`check`**: report on every connection and on the rule.
- No argument: ask which of the two, with `new` first.

## Mode: new

1. **Interview**, in chat, one question at a time and only what the request left out:
   - **What it reaches and its kind**: `rest` for an HTTP API, `generic` for any command line tool, or a name of the developer's own. Read the matching `${CLAUDE_PLUGIN_ROOT}/shared/connections/{kind}.md` when the plugin ships one.
   - **The profile name**: a lowercase slug that says system and environment (`billing-qa`), proposed from the answers. It must not already exist: run `connection list`, and when it does, stop and say the profile is edited by hand, never overwritten.
   - **The environment and whether it is production.** Apply the name rule of `connections.md` to the proposed name, show what it decides, and ask only to confirm or correct it. An unrecognised name is production.
   - **The variable names the profile needs**, never their values: `BASE_URL` and `TOKEN` for a `rest` connection, the variable a tool reads (`MONGO_URI`) for a `generic` one.
   - **Whether a project's own env file supplies them** (`.env.qa`): then the profile names it with `CONNECTION_ENV_FILE=<path>` and holds no copy.
   - **Where it is registered**, if anywhere: a namespace or product (`namespace/product`), and for a product the environment it links.
2. **Preview, then one yes per write set.** Show exactly what will be written: the profile file's path and its lines (placeholders only), the registry entry and the config file it joins, and the rule file when it is missing or stale. Wait for an explicit yes to the whole preview; anything else writes nothing. A change to the preview needs a new showing.
3. **Write the profile.** `{connections home}/{profile}.env`, the home being `~/.sdlc/.connections` or `$SDLC_CONNECTIONS_HOME` (`connection list` reports it as `home`). It holds `CONNECTION_KIND`, `CONNECTION_PRODUCTION` only where the developer wants to override the name's reading, `CONNECTION_ENV_FILE` where one was named, and one empty line `NAME=` per variable, never a value. Create the folder if it is missing. Then tell the developer which file and which keys to fill in themselves, in an editor, and stop short of reading it back.
4. **Write the registry entry**, when one was asked for. Read the config file first (`~/.sdlc/{namespace}/namespace.json` or `{namespace}/{product}/product.json`; it holds no secret), keep every other key, and add `{"profile": ..., "environment": ..., "production": ...}` to `connections`, leaving out what was not asked for and replacing an entry of the same profile. A product's list replaces its namespace's, so say when this one will hide the namespace's. Then run `resolve --new --title check` (with `--context` when the session has one): a non-zero exit names the file at fault; fix it and run it again.
5. **Write the rule.** `~/.claude/rules/connections.md` holds the text between the `connections-rule` markers of `connections.md`, copied verbatim, with `{SDLC_PY}` replaced by the absolute path that `${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py` names on this machine. Overwrite only a file that holds those markers or does not exist; say so and stop for any other. The rule holds this machine's plugin path, so say that it is local to the machine, and that a plugin update moves the path (`check` finds it stale). Never add it to a repository's ignore file yourself; offer the line.
6. **Print the suggested permission entries and edit nothing.** For the developer to add to their own `settings.json`, as suggestions to adapt to its permission syntax: a deny for reading env files (`Read(**/.env*)`) and for the connections home (`Read(~/.sdlc/.connections/**)`, using the real path), and an ask for `connection run` against each production profile. Say plainly that this skill never edits `settings.json`.
7. **Recommend read-only credentials** for a production profile, in one line: the runner cannot tell a write, so a credential that cannot write is the guard that holds.
8. **Verify.** Run `connection check` and `connection list` (with `--context` when one was used) and report the profile's row: kind, production mark and what decided it, registered or not. Missing values are expected until the developer fills them in; say that.

## Mode: check

1. Run `connection list` (with `--context` when the session has one) and `connection check`, and report one line per profile: name, kind, production mark and its source, registered or not, each problem and warning. A registered profile with no file on this machine is a gap to name.
2. Check the rule: `~/.claude/rules/connections.md` exists, holds the markers, equals the marked block of `connections.md` with this machine's path in place of `{SDLC_PY}`, and that path exists. Report each of these that fails. A stale rule is rewritten after one yes, as in step 5 above.
3. Report names only. Never open a profile, never print a value, and never run a command through a profile: that is `/sdlc:query`.

## Report

What was written (each path), what the developer must do themselves (fill in the values, add the permission entries), the check's result, and anything left undone.

## Invariants

- Never ask for, read, print or store a secret. A profile is written with empty placeholders, and only profile and key names are ever read.
- Never open a profile or an env file with a file tool or a shell command; `connection check` and `connection list` are the only way.
- Never overwrite an existing profile. Never edit `settings.json` or any permission file.
- Writes only: one new profile file, a `connections` entry in a namespace or product config file, and the rule file. Each after the yes to its preview.
- Never run a command through a profile, and never reach an external system.
