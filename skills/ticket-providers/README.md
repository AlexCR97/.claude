# Ticket providers

This directory is **not a skill** — it holds no `SKILL.md` and is never invoked directly. It holds one subdirectory per ticket source, discovered by glob. Adding a source is adding a directory; no `SKILL.md` changes.

A provider directory is trusted **code**, not configuration. `provider.py` is imported and executed by `ticket-common/ticket.py`. Add a source the way you would add a module to the suite, not the way you would drop in a config file.

---

## The two halves

**`provider.json` is the cheap index.** It is always read, for every source, on every `resolve`. It is machine-parseable with stdlib `json` and no third-party dependency — which is also why it is JSON rather than YAML.

```json
{
  "source": "ado",
  "kind": "remote",
  "prefixes": ["ado", "azdo"],
  "nouns": { "singular": "work item", "plural": "work items" },
  "id": { "pattern": "\\d+", "shape": "numeric work item id" },
  "formats": { "comment": "html", "body": "html" },
  "capabilities": {
    "fetch": true, "new": false, "publish": true,
    "drift": true, "related": true, "attachments": true
  }
}
```

`ticket.py` gates every verb on `capabilities` **before** the module is loaded, so an absent capability is exit 3 and there is no code path for a driver to improvise past.

**The role `.md` files are the expensive references.** A driver opens only the one role file for its own step, only for the resolved source, and **never another source's files**.

| Role file | Answers | Read by | Gates capability |
| --- | --- | --- | --- |
| `provider.json` | capabilities, prefixes, id shape, nouns, comment format | all, via `resolve` | — |
| `config.md` | what `{source}/config.json` holds, how credentials are acquired and validated | `ticket-init` | — |
| `fetch.md` | how raw data lands in `raw/`, traversal policy, attachment rules, how `ticket.json` is refreshed | `ticket-fetch` | `fetch` |
| `new.md` | how a ticket is created here | `ticket-new` | `new` |
| `schema.md` | where the content is on disk and the logical→physical field map | `ticket-digest`, `ticket-refine` | — |
| `types.md` | this source's native type and tag/label vocabulary → one canonical type | `ticket-fetch`, `ticket-new` | — |
| `links.md` | ticket / comment / attachment URL patterns | `ticket-digest`, `ticket-plan`, `ticket-checkpoint` | — |
| `publish.md` | where a refinement summary goes, in what markup, via what verb, which template | `ticket-refine` | `publish` |
| `drift.md` | how to tell the local snapshot is stale, as exit 0/1/2 | `ticket-resume` | `drift` |
| `provider.py` (+ private `_*.py`) | every network call and every credential | never read — invoked via `ticket.py` | — |

`config.md`, `schema.md`, `types.md` and `links.md` are **required of every source**. The other four are present exactly when the matching capability is `true`. `python ticket-common/ticket.py sources --check` validates that agreement, and a mismatch is an error.

### Absence is the mechanism

Two deliberate gaps are how the suite enforces its rules without a single `if source == …` branch in any driver:

- **`local/fetch.md` is absent** and `capabilities.fetch` is `false`, so `ticket-fetch` refuses `local` structurally. Fetch being remote-only falls out of the module system, not out of driver logic.
- **`ado/new.md` and `github/new.md` are absent**, so `ticket-new` refuses remote sources — and the absence documents that creating an upstream ticket is out of scope rather than forgotten.

A source directory may hold only some of the optional role files. Treat each as present-or-absent independently, and **never substitute another source's module for a missing one**. A missing module is a reported gap.

---

## The anti-leak rule, inverted

A driver must never name a source. The converse binds just as hard:

> **A role file must never restate a driver's step ordering, its output template, or anything in `ticket-common/`.**

A fact stated in both places will drift, and the role-file copy will be the stale one. Say where the acceptance criteria live; do not say what the digest does with them. Say what markup a comment must be in; do not restate the three refinement rounds.

The one legitimate crossing point between the source axis and the type axis is `types.md`, which maps this source's vocabulary onto a canonical type — **the mapping only**. A source file must never encode a type's behaviour, and a type file must never mention a source.

---

## Adding a source

Create the directory, write `provider.json`, then answer six questions in `schema.md`. They are fixed, because they are exactly what `ticket-digest` and `ticket-refine` need and nothing more:

1. **Where does the content live on disk?** Which file under `raw/`, and in what shape.
2. **What is the logical→physical field map?** For `id`, `type`, `title`, `state`, `description`, `acceptance criteria`, `assignee`, `labels` — and **which of them this source simply does not have**. A field a source lacks is stated as absent, so the driver omits the row rather than inventing one.
3. **What markup is the prose in?** HTML, markdown, or plain text. This is what tells the digest how to render it.
4. **How are comments, mentions and cross-references enumerated?** Where the thread is, how it is ordered, and how a mention or a reference to another ticket is recognised.
5. **How are attachments enumerated, and how is a failed download signalled?** Including the on-disk naming scheme and which field holds the display name.
6. **How are related tickets and relation kinds enumerated?** Or, where `capabilities.related` is `false`, say so plainly.

Then write `types.md`, `links.md`, `config.md`, `provider.py`, and whichever of `fetch.md` / `new.md` / `publish.md` / `drift.md` the capabilities claim. Finally run `sources --check`.

### What `provider.py` must expose

`ticket.py` calls these and nothing else. Each is handed a `ctx` dict (source, id, manifest, config, absolute paths) and the list of unrecognised command-line flags, so a provider can take its own options without the front door knowing about them.

| Function | Returns |
| --- | --- |
| `init(ctx, extra)` | a report dict; writes `{source}/config.json` |
| `fetch(ctx, extra)` | a report dict; writes `raw/` and refreshes `ticket.json` |
| `new(ctx, title, ticket_type, extra)` | a report dict; creates the ticket root and `ticket.json` |
| `publish(ctx, text, extra)` | a report dict |
| `drift(ctx, extra)` | a report dict carrying `is_stale`; `ticket.py` maps it to exit 0 or 2 |
| `auth_status(ctx)` | a report dict; **never** a credential |

Only the functions whose capability is `true` need to exist.

---

## Known limitations, recorded rather than discovered

- **Cross-repo GitHub references (`gh:owner/repo#42`) are out of scope.** The `github/{number}/` layout forecloses them: two repositories' issue #42 would collide in one directory. Supporting them means changing the layout, not patching the resolver.
- **Creating an upstream ticket is out of scope** for both remote sources. The door is left open — add a `new.md` and flip the capability.
