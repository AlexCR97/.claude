# Generic connection

Instructions for a connection of kind `generic`, and the base for every other kind: any system you reach with a command line tool (`mongosh`, `psql`, `temporal`, `kubectl`, `redis-cli`). The policy is [`../connections.md`](../connections.md); read it first.

## Calling

1. **Find the profile.** `connection list` (with `--context` inside a product). Use the profile the user named; with none named and several that fit, ask which. Check its `kind`, and its `production` mark before anything else.
2. **Learn the variable names**, never the values: `connection check` lists each profile's keys. Use those names in the command.
3. **Compose the command so the child expands the variable**, because the runner starts it without a shell and the variables exist only in its environment:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- sh -c 'mongosh "$MONGO_URI" --quiet --eval "db.getCollectionNames()"'
   ```

   Use `sh -c` where a POSIX shell exists, `pwsh -NoProfile -Command` or `python -c` (reading `os.environ`) otherwise. Quote the inner command so your own shell does not expand `$MONGO_URI` first, where it would be empty.
4. **Preview when unsure** with `--dry-run`: it shows the variable names, the command with any value masked, and whether the run would be refused, and runs nothing.
5. **Read the envelope.** `exit_code` is the command's own, and a failing command still returns exit 0 from the verb; `stdout` and `stderr` are masked. A `***` in the output is a credential that the command printed.

## Rules for the command

- **Read-only first.** Prefer the tool's read form: a `find`, a `SELECT`, `get`, `list`, `describe`, `--dry-run`. A command you cannot read as read-only is a write and asks first.
- **Never print a variable.** No `echo "$TOKEN"`, no `env`, no `printenv`, no `set`, no debug or verbose flag that echoes a connection string or header; masking is a net, not a plan.
- **Prefer a tool that reads the variable itself.** Once the child shell expands `$VAR`, the value is an argument of the tool, visible in this machine's process list while it runs, though never in your context. Where the tool reads its credential from the environment (`PGPASSWORD`, `MONGODB_URI`-style variables the tool documents) or from a config on stdin, use that and leave the argument out.
- **Keep the secret out of files.** Do not write the command's output to a file unless the user asked for it, and never for a production connection.
- **A tool that asks for a password** reads it from its own environment variable or a `--password-stdin`; never type one into a prompt or pass it as an argument you wrote.
- **Bound the work.** Add a limit to a query (`--limit`, `LIMIT`, `head`) so a large collection does not flood the output; the envelope holds all of it.

## When it fails

- **Exit 4:** a refusal. Its `reason` says production, a `sensitive` target, or both. Ask the user, and pass `--approved` only on their yes, which for production means their message names the connection.
- **Exit 1:** the profile is missing, has problems (`connection check` says which), or the command could not be started. Fix the profile or the command; never work around it by reading the file.
- **A non-zero `exit_code`:** the system or the command failed. Read the masked `stderr` and adjust the command, not the credentials.
