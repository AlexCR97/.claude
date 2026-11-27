# Database connection

Instructions for a connection of kind `database`: a SQL or NoSQL database reached with its command line client (`psql`, `mysql`, `sqlcmd`, `mongosh`, `redis-cli`). Everything in [`generic.md`](generic.md) applies; this adds what is particular to databases. The policy is [`../connections.md`](../connections.md).

## The profile

A `database` profile holds the credential in one of two shapes. You read only the key names, with `connection check`, never a value:

| Shape                         | Keys                                                                                  | Use                                                                                                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Connection string (preferred) | `CONNECTION_STRING`, or `DATABASE_URL` for a SQL database, or `MONGODB_URI` for MongoDB | The norm: use the name the project or the tool already uses. Many projects' `.env` files hold exactly this, so a profile can point at one with `CONNECTION_ENV_FILE`. |
| Parts                         | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`                              | For a tool that takes the parts separately, and to keep the password out of the command's arguments (see below).                                           |

The parts are prefixed `DB_` because `USER` and `USERNAME` are already environment variables on Unix and Windows, and a profile key of that name would replace the real one inside the command; do not use them, or a bare `PASSWORD`, as keys.

## String or parts

A connection string reaches the tool as an argument, so while the tool runs it is visible in this machine's process list, though never in your context. Where the tool reads its own variables, the credential never becomes an argument: `psql` reads `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD`, and a profile may hold those names directly. Use the string as the norm, and choose the tool's own variables when the process list matters.

## Calling

Wrap the client as [`generic.md`](generic.md) says, so the child expands the variable.

```
# a connection string, passed as an argument
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- sh -c 'psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At -c "select count(*) from orders"'

# the tool's own variables: no shell, and no argument carries the credential
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- psql -v ON_ERROR_STOP=1 -At -c "select count(*) from orders"

# MongoDB
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- sh -c 'mongosh "$MONGODB_URI" --quiet --eval "db.getCollectionNames()"'
```

- **Read-only first.** `SELECT`, `find`, `count`, `aggregate` without `$out` or `$merge`, `SHOW`, `DESCRIBE`, `EXPLAIN`. Anything that inserts, updates, deletes, creates, alters, drops, truncates, restores or imports is a write and asks first, with the exact command shown. A statement you cannot read as read-only is a write.
- **Ask the engine to refuse writes** where it can, as a second guard: for PostgreSQL `PGOPTIONS="-c default_transaction_read_only=on"` set inside the wrapped command. The runner cannot tell a write, and a production profile should hold read-only credentials ([`../connections.md`](../connections.md)).
- **Bound every query.** `LIMIT`, `.limit()`, a `WHERE` on an indexed column; count or aggregate before you list rows. A large table or collection is a read that can hurt the system: say so before running it, and prefer a replica.
- **Ask for the columns you need.** Rows can hold personal data; never `SELECT *` or dump a collection into the reply, and never save the rows to a file unless the user asked, and not at all from a production connection.
- **Never print the connection string,** and do not run a statement that returns one (`SHOW`, `\conninfo` can echo the host or user).

## When it fails

An authentication error means the credential lacks the right: report it and ask, never try another profile or a guessed password. A timeout means the system or the query is slow (the runner stops a command after 120 seconds, or `SDLC_CLI_TIMEOUT`): narrow the query before you retry. A connection refused or an unknown host is the system's, or the profile's host or port; report it.
