# Ticket providers

This directory is **not a skill** — it holds no `SKILL.md` and is never invoked directly. It holds one subdirectory per ticket source, discovered by glob. Adding a source is adding a directory; no `SKILL.md` changes.

A provider directory is trusted **code**, not configuration. `provider.py` is imported and executed by `ticket-common/ticket.py`. Add a source the way you would add a module to the suite, not the way you would drop in a config file.

**Scripts are for work whose result must be byte-identical every run**: downloading a ticket into `raw/`, creating a local one, hashing a file. Anything that talks to a ticket system's write API, or that is a judgement about what changed, is a recipe the agent follows with the source's own CLI. See [Contracts and recipes](#contracts-and-recipes).

---

## The two halves

**`provider.json` is the cheap index.** It is always read, for every source, on every `resolve`. It is machine-parseable with stdlib `json` and no third-party dependency — which is also why it is JSON rather than YAML.

```json
{
  "source": "ado",
  "kind": "remote",
  "prefixes": ["ado", "azdo"],
  "coordinates": { "organization": "namespace", "project": "product" },
  "url": { "canonical": "https://dev.azure.com/{organization}/{project}/_workitems/edit/{id}" },
  "nouns": { "singular": "work item", "plural": "work items" },
  "id": { "pattern": "\\d+", "shape": "numeric work item id" },
  "formats": { "comment": "html", "body": "html" },
  "capabilities": {
    "fetch": true, "new": true, "update": true,
    "drift": true, "related": true, "attachments": true
  }
}
```

`coordinates` is what maps this source's own concepts onto the tickets home's. It names each value that locates a ticket upstream and the level it is bound at — `namespace` for an account-level one such as an organization or an owner, `product` for one such as a project or a repository. A binding under `sources.{source}` in a namespace's or product's `config.json` holds exactly these, and a ticket's own `ticket.json` records them at fetch. A source with nothing upstream declares `{}`, and is then usable in every product without an init. The key is required.

`url.canonical` is the one address recorded for a ticket whichever form was pasted. It is optional: a source without it records whatever its fetch learns. The manifest holds no pattern for reading a pasted address. The driver reads one, using the source's `links.md` → *Reading an address*, and hands `resolve` the id and each coordinate as `--coordinate`.

`ticket.py` gates every verb on `capabilities` **before** the module is loaded, so an absent capability is exit 3 and there is no code path for a driver to improvise past.

**The role `.md` files are the expensive references.** A driver opens only the one role file for its own step, only for the resolved source, and **never another source's files**.

| Role file                         | Answers                                                                                          | Kind     | Read by                                                             | Gates capability |
| --------------------------------- | ------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------- | ---------------- |
| `provider.json`                   | capabilities, prefixes, coordinates, canonical address, id shape, nouns, comment format          | —        | all, via `resolve`                                                  | —                |
| `config.md`                       | what a binding holds and at which level, what the CLI must have, how a sign-in is checked        | contract | `ticket-setup`                                                      | —                |
| `fetch.md`                        | how raw data lands in `raw/`, traversal policy, attachment rules, how `ticket.json` is refreshed | contract | `ticket-fetch`                                                      | `fetch`          |
| `new.md`                          | how a ticket is created here — a local script, or upstream with the source's CLI behind a yes    | both     | `ticket-create`                                                     | `new`            |
| `update.md`                       | how an upstream ticket is changed: the fields, the commands, what guards the write               | recipe   | `ticket-update`                                                     | `update`         |
| `schema.md`                       | where the content is on disk and the logical→physical field map                                  | contract | `ticket-digest`                                                     | —                |
| `types.md`                        | this source's native type and tag/label vocabulary → one canonical type                          | contract | `ticket-fetch`, `ticket-create`                                     | —                |
| `links.md`                        | how to read a pasted address, and ticket / comment / attachment URL patterns                     | contract | `ticket-fetch`, `ticket-plan`, `ticket-digest`, `ticket-checkpoint` | —                |
| `drift.md`                        | how to tell the local snapshot is stale, ending in current, changed or could not be checked      | both     | `ticket-resume`, `ticket-plan`, `ticket-digest`, `ticket-update`    | `drift`          |
| `provider.py` (+ private `_*.py`) | the script halves: binding, init, fetch, and a local store's new and drift                       | —        | never read — invoked via `ticket.py`                                | —                |

`config.md`, `schema.md`, `types.md` and `links.md` are **required of every source**. The others are present exactly when the matching capability is `true`: a capability means *this source has a role file for it*, whether that file is a contract or a recipe. `python ticket-common/ticket.py sources --check` validates that agreement and that `coordinates` names real levels; a mismatch is an error.

### Contracts and recipes

A role file is one of two things, and the glossary defines both:

- A **contract** defines what a script must produce or what a ticket on disk must hold. The script and every later skill depend on it exactly, so it is precise and it changes with care. `fetch.md`, `schema.md`, `types.md`, `links.md`, `config.md`, and `drift.md` and `new.md` where a script is behind them (`local`).
- A **recipe** tells the agent how to do something with the source's own CLI: `gh` or `az`. Its commands are examples, not an allowlist, so the agent can use any call the task needs, and a task the recipe never imagined — adding a tag, say — needs no new script. `update.md`, and `drift.md` and `new.md` for `github` and `ado`.

A recipe never replaces a gate. The skill that follows it asks for an explicit yes before a write, checks the ticket has not moved, and uses whatever guard the recipe names. A source's CLI holds the sign-in; nothing here reads or stores a token.

### Absence is the mechanism

Deliberate gaps are how the suite enforces its rules without a single `if source == …` branch in any driver:

- **`local/fetch.md` is absent** and `capabilities.fetch` is `false`, so `ticket-fetch` refuses `local` structurally. Fetch being remote-only falls out of the module system, not out of driver logic.
- **`local/update.md` is absent** and `capabilities.update` is `false`, so `ticket-update` refuses `local`: a local ticket is edited directly, there being no upstream to change.

A source directory may hold only some of the optional role files. Treat each as present-or-absent independently, and **never substitute another source's module for a missing one**. A missing module is a reported gap.

---

## The anti-leak rule, inverted

A driver must never name a source. The converse binds just as hard:

> **A role file must never restate a driver's step ordering, its output template, or anything in `ticket-common/`.**

A fact stated in both places will drift, and the role-file copy will be the stale one. Say where the acceptance criteria live; do not say what the digest does with them. Say what markup a comment must be in; do not restate the digest's steps.

The one legitimate crossing point between the source axis and the type axis is `types.md`, which maps this source's vocabulary onto a canonical type — **the mapping only**. A source file must never encode a type's behaviour, and a type file must never mention a source.

---

## Adding a source

Create the directory, write `provider.json`, then answer six questions in `schema.md`. They are fixed, because they are exactly what `ticket-digest` needs and nothing more:

1. **Where does the content live on disk?** Which file under `raw/`, and in what shape.
2. **What is the logical→physical field map?** For `id`, `type`, `title`, `state`, `description`, `acceptance criteria`, `assignee`, `labels` — and **which of them this source simply does not have**. A field a source lacks is stated as absent, so the driver omits the row rather than inventing one.
3. **What markup is the prose in?** HTML, markdown, or plain text. This is what tells the digest how to render it.
4. **How are comments, mentions and cross-references enumerated?** Where the thread is, how it is ordered, and how a mention or a reference to another ticket is recognised.
5. **How are attachments enumerated, and how is a failed download signalled?** Including the on-disk naming scheme and which field holds the display name.
6. **How are related tickets and relation kinds enumerated?** Or, where `capabilities.related` is `false`, say so plainly.

Then write `types.md`, `links.md`, `config.md`, `provider.py`, and whichever of `fetch.md` / `new.md` / `update.md` / `drift.md` the capabilities claim. Finally run `sources --check`.

### What `provider.py` must expose

`ticket.py` calls these and nothing else. Each is handed a `ctx` dict and the list of unrecognised command-line flags, so a provider can take its own options without the front door knowing about them. `ctx` carries the source, the id, the manifest, the `product` the ticket is filed under, that product's effective `config` and `binding`, the ticket's `coordinates` — its own where `ticket.json` records them, else the binding, else the `--coordinate` flags given — and, for a ticket, its `location` and absolute `paths`.

**A provider reads its coordinates from `ctx["coordinates"]` and nowhere else.** It never opens a `config.json` or builds a ticket path itself; that is what lets one source be bound in any number of products. It stores no credential: the source's own CLI (`az`, `gh`) holds it.

| Function                              | Returns                                                                                                                                                                                                                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `binding(ctx, extra)`                 | `{"coordinates", "defaults_applied", "inherited"}` — what an init would bind: from the flags, else `ctx["binding"]`, else this source's defaults. Validates nothing                                                                                                      |
| `init(ctx, extra)`                    | a report dict; checks the CLI is installed, signed in and has what the recipes need, and validates `ctx["coordinates"]` through it. The front door writes the binding                                                                                                    |
| `fetch(ctx, extra)`                   | a report dict; writes `raw/` and refreshes `ticket.json`, including its `coordinates`. Only a source with `fetch`                                                                                                                                                        |
| `new(ctx, title, ticket_type, extra)` | a report dict; creates the ticket directory and `ticket.json`. **Only a source whose `new.md` is a script** — a remote source's is a recipe, and `ticket.py new` refuses it with the path of the file to read                                                            |
| `drift(ctx, extra)`                   | a report dict carrying `is_stale`; `ticket.py` maps it to exit 0 or 2. **Only a source whose `drift.md` is a script**, for the same reason                                                                                                                               |
| `set_parent(ctx, ref, dry_run=False)` | optional; rewrites a stored `parent` in this source's own record, for `move`, raising `TicketError` where it cannot. `dry_run` fails exactly where a real run would and writes nothing, so `move` can check before renaming. Without it, only `ticket.json` is rewritten |

`binding` and `init` always exist. The others need to exist only where the capability is a script.

---

## Known limitations, recorded rather than discovered

- **Cross-repository GitHub references (`gh:owner/repo#42`) are out of scope.** A product is bound to one repository and holds its issues at `github/{number}/`, so two repositories' issue #42 would collide in one product. A second repository is a second product; a GitHub Projects board spanning repositories cannot be bound, for the same reason.
- **Assignee, iteration and area path** cannot be set on create or update for either remote source, and **GitHub Projects boards** are not touched.
