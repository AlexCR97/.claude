---
name: query
description: Asks a question of an external database or API through a named connection profile, without the model ever seeing its credentials, and prints the answer. Use only when the request names a connection or a system that has one, such as "how many orders are in billing-qa"; never to go looking for one.
argument-hint: "<connection> <what to look at> [save] [ship]"
---

# Query

Answer the question `$ARGUMENTS` asks of the connection it names, by running a command through the `connection` verb so the credentials never reach the model. Run scripts as `python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" <verb>` (`python3` where that is the interpreter's name). The policy, the profile format and the verb are `${CLAUDE_PLUGIN_ROOT}/shared/connections.md`; read it first. Terms mean what `${CLAUDE_PLUGIN_ROOT}/GLOSSARY.md` says.

## Inputs

- **The connection**: a profile name, or a system the request names that has one. Never infer one the request does not name, and never offer to query on the model's own initiative: `plan` and `implement` do not call this skill, and neither does anything else that was not asked.
- **What to look at**: the question, in the user's words.
- **`save`**: the literal word. Save the result under a ticket's `artifacts/` (see Saving).
- **A ticket**, optional: only for `save`, and for the session's context. Without one the skill works the same and has nowhere to save.
- **`ship`**: the [ship flag](../../shared/conventions.md#ship-runs), never part of the question. Under it the run may use a connection only when its invocation or the ticket names it, as Policy says.

## Steps

1. **Find the connection.** Run `connection list` (with `--context {namespace}[/{product}]` when the session has one) and match the name. No match: name the profiles that exist and stop; never invent a profile, and never open a profile file. Say the connection's kind and its production mark and what decided it.
2. **Read the instructions for its kind**: `${CLAUDE_PLUGIN_ROOT}/shared/connections/{kind}.md` when the plugin ships one, else `generic.md`, and the developer's own notes for the kind in `~/.claude/docs/connections/{kind}.md` when that file exists. `connection check` lists the profile's variable names; use them, never their values.
3. **Decide whether the command reads or writes**, and apply the gate of `connections.md`:
   - A read-only command on a non-production connection runs without asking.
   - A write on any connection: show the exact command and wait for an explicit yes; the yes covers that command only. Under `ship` this is a hard stop.
   - A production connection only when the user's current message names it, and read-only unless that message also asks for the write. Under `ship`, any touch of production is a hard stop.
   - A command you cannot read as read-only is a write.
4. **Run it** through the verb, `connection run [--context ...] <profile> -- <wrapped command>`, composed as the kind's instructions say. Add `--approved` only after the yes or the message that names a production connection; without it a production or `sensitive` target is refused with exit 4, and that refusal is final: report its `reason`, never look for another way to the same system. Use `--dry-run` first when unsure what the command will do or whether it will be refused. Bound the query so a large result does not flood the output.
5. **Answer.** Give the answer from the masked output: the figures or rows asked for, the command that produced them with the profile named, and how much was read (a limit hit, a page count). A `***` in the output is a credential the command printed: say so and do not try to recover it. Never print a variable, and never put a value in the reply.
6. **Save**, only on the word `save`. Never from a production connection: say that results of one are printed only, because `/sdlc:export` zips whole ticket directories and a saved result would leave the machine with it. Otherwise, with a ticket, write the masked output under its `artifacts/shared/` as `${CLAUDE_PLUGIN_ROOT}/shared/artifacts.md` says: append-only, named `{name}.output.{ext}` by the format the whole file parses as (`probe.{profile}.output.json`, else `.txt`), a new file beside an existing one, and mention in one line that an export includes it. Without a ticket there is nowhere to save: say so and keep the answer in the reply.

## Policy under a ship run

A ship run reaches a connection only when its invocation or the ticket names it. A read-only call on a non-production connection runs unattended. Any write, and any touch of a production connection, is a hard stop: run `/sdlc:checkpoint <ref> ship`, send a push notification with the `PushNotification` tool (load it with ToolSearch, `select:PushNotification`, when it is deferred) naming the ticket and what waits, and wait for an explicit yes. Say each decision as it is made, with its cost if wrong.

## Report

The answer, the command run (the profile named, never a value), the connection's production mark, anything refused and why, and where a result was saved.

## Invariants

- Reaches an external system only through `connection run`, and only for a connection the request named.
- Never asks for, reads, prints or stores a secret, and never opens a profile, an env file or the connections home.
- Never writes through a connection without the yes for that command, and never touches production unless the user's current message names it.
- Never saves a production result, and never overwrites a saved one.
- Never changes a ticket, a config file or the workspace.
