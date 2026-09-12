# Resolution and paths

Read this only when the resolver's output is disputed — when a path is not where a driver expected it, an id resolved to the wrong source, or an exit code needs interpreting. In the ordinary case step 1 of every driver already has everything it needs.

---

## The one command

```
python "{skills}/ticket-common/ticket.py" <verb> [<ref>] [--source S] [flags]
```

| Verb | Does |
| --- | --- |
| `sources [--check]` | Lists every provider and its capability matrix. `--check` validates that each manifest's capabilities and its role files agree. |
| `resolve <ref> [--type T] [--require a,b]` | The source, the id, the type, every absolute path, the capabilities, `ticket.json`, and what is on disk. |
| `list` | Every ticket on disk across every source, newest first. |
| `init --source S` | Per-source connection setup. |
| `fetch <ref>` | Refreshes the local snapshot. Remote sources only. |
| `new --source S --title "…" [--id SLUG] [--type T]` | Creates a ticket in a store that supports it. |
| `publish <ref> --file F [--delete-after-post]` | Posts a summary back to the source. |
| `drift <ref>` | Has the ticket moved since it was fetched? |
| `auth-status [--source S]` | Each source's credential state, never the credential. |

Flags a verb does not recognise are passed through to the provider untouched, so the front door never has to know what a given source needs in order to connect.

---

## How a reference resolves

A reference is `[source:]id`. Resolution is implemented in `ticketlib/sources.py` and runs in this order:

1. **An explicit prefix** — `ado:12345`, `gh:42`, `local:auth-fix`. Every source's own name works as a prefix, plus any alias its `provider.json` declares.
2. **A bare token** — scan every source for a ticket directory of that name. Exactly one hit wins. **Two or more exits 3** and lists them; the fix is to name the source, never to guess.
3. **The root `config.json`'s `default_source`** — used only when the token is on disk nowhere.

An id is validated against the source's `id.pattern` once the source is known, so `ado:not-a-number` fails at resolution rather than at the API.

---

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | ok — for `drift`, also "up to date" |
| 1 | error / not initialized |
| 2 | `--require` unmet, **or** `drift` found the ticket moved |
| 3 | ambiguous bare id, or the source declares this capability absent |
| 4 | the legacy `~/.az-workitems` layout was detected → tell the user to run `/ticket-init` to migrate |
| 5 | ticket not found |

Exit 3 on an absent capability is structural, not advisory: the verb refuses before any provider code loads. Report it as a gap. Never substitute another source's behaviour for it, and never hand-roll the call the provider declined to make.

Exit 4 is why no driver and no deprecated alias contains the old path. The resolver detects the legacy tree; the driver only relays the message.

`--require` takes a comma-separated subset of `config, ticket_dir, ticket_json, raw, digest, plan, journal`. An unmet requirement exits 2 with a hint naming the skill that would satisfy it.

---

## Paths

**Every path in `resolve`'s output is absolute.** Neither the file tools nor a quoted shell argument expands `~`, so the resolver expands it once and no driver ever has to.

```
~/.tickets/
├── config.json                 {"default_source": "…"} — the only key
└── {source}/
    ├── config.json             this source's coordinates and cached credential
    └── {id}/
        ├── ticket.json         source, id, title, type, native_type, state, url, last_fetched_at
        ├── digest.md           ← ticket-digest
        ├── journal.md          ← ticket-checkpoint only; read only by ticket-resume
        ├── plan.md             ← ticket-plan
        ├── raw/                ← ticket-fetch, or the source of truth for a local store
        └── artifacts/          ← ticket-plan and ticket-implement (see ARTIFACTS.md)
```

A ticket root holds **nothing but those six entries**. Never write a generated file directly into it.

`TICKETS_HOME` overrides the root, which is how a test runs against a scratch tree without touching real data.

---

## `ticket.json`

The file that keeps source-specific URL patterns out of every driver and every template.

| Key | Notes |
| --- | --- |
| `source`, `id` | The resolved identity. |
| `title`, `state` | As the source last reported them. |
| `type` | One of the canonical types in `ticket-types/`. |
| `native_type` | The source's own word for it, kept untouched alongside. |
| `url` | The ticket's web address, or **`null`** where the source has none. |
| `last_fetched_at` | When the snapshot was taken, in UTC. |

**Read `url` and degrade to plain text when it is `null`.** A local store has no web address, and a digest that prints a broken link is worse than one that prints `#42: Cache the authorization lookup` as text.

A record may also carry a source-specific `fingerprint` (whatever that source's `drift.md` compares against) and `"incomplete": true` where a field could not be derived. An absent `title` is null — never invented.

---

## Credentials

`config.token` is always replaced by its status string in anything the front door prints. No verb emits a credential, and no driver reads one: acquiring, caching and refreshing all happen inside the provider module.
