# Resolution and paths

Read this only when the resolver's output is disputed — when a path is not where a driver expected it, a reference resolved to the wrong ticket, a ticket was filed under an unexpected product, or an exit code needs interpreting. In the ordinary case step 1 of every driver already has everything it needs.

The terms used here — namespace, product, binding, coordinates, filing, session context — mean exactly what `GLOSSARY.md` says.

---

## The one command

```
python "{skills}/ticket-common/ticket.py" <verb> [<ref>] [--source S] [--in X] [--context X] [flags]
```

| Verb                                                             | Does                                                                                                                                                                                               |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sources [--check]`                                              | Lists every provider, its capabilities and its coordinates. `--check` validates that each manifest's capabilities, role files and coordinates agree.                                               |
| `resolve [<ref>] [--type T] [--require a,b]`                     | The location, the type, every absolute path, the capabilities, `ticket.json`, the effective config and where each value came from, and what is on disk — or, for a ticket not on disk, its filing. |
| `list`                                                           | Every ticket on disk, newest first, with its product and resolved parent.                                                                                                                          |
| `namespaces [--in X]`                                            | Every namespace and product with their bindings; with `--in`, one level's effective config and where each value came from. Exits 5 when that level does not exist.                                 |
| `defaults [--namespace NS] [--product NS/PRODUCT]`               | Shows the default namespace and default products, or sets them. `default` unsets either.                                                                                                           |
| `init --source S [--in NS/PRODUCT] [--propose] [provider flags]` | Binds a source under a product. `--propose` reports the coordinates, where they would be filed and any problem, and writes and validates nothing.                                                  |
| `init --in NS[/PRODUCT]`                                         | Creates a namespace or product with no binding.                                                                                                                                                    |
| `fetch <ref>`                                                    | Refreshes the local snapshot. Remote sources only. A ticket not yet on disk is filed first.                                                                                                        |
| `new --source S --title "…" [--id SLUG] [--type T] [--propose]`  | Creates a ticket in a store that supports it, filed by the filing rules. `--propose` reports where it would be filed and whether the id is taken, and creates nothing.                             |
| `publish <ref> --file F [--delete-after-post]`                   | Posts a summary back to the source.                                                                                                                                                                |
| `drift <ref>`                                                    | Has the ticket moved since it was fetched?                                                                                                                                                         |
| `move <ref> --to NS/PRODUCT [--dry-run]`                         | Re-files a ticket: renames its directory, rewrites every `parent` that would stop resolving, reports the links the move breaks. See [Moving](#moving).                                             |
| `auth-status [--source S]`                                       | Each source's credential state, once per credential, never the credential.                                                                                                                         |
| `scan-roots [--in NS[/PRODUCT]] [--set [DIR ...]]`               | One level's scan roots and the effective list with where it came from. `--set` replaces that level's list with the given directories, each checked to exist; with none it empties it.              |

**`--in` restricts; `--context` prefers.** `--in {namespace}[/{product}]` narrows what a reference can mean and where a new ticket can be filed. `--context` is how a driver passes the session context: it wins a tie and decides filing, but it never hides a ticket filed elsewhere. They are separate flags so a preference can never act as a restriction.

Flags a verb does not recognise are passed through to the provider untouched, so the front door never has to know what a given source needs in order to connect.

---

## The session context

`/ticket-context` sets it, and it lives in the conversation, never on disk: it lasts exactly as long as the session, needs no cleanup, and two sessions — one on office work, one on personal — cannot leak into each other.

**Every driver, when the session has one:**

- passes `--context {context}` on every `ticket.py` call that takes it — `resolve`, `list`, `fetch`, `new`, `publish`, `drift`, `move`;
- starts its first output line with `Ticket context: {context}`, which keeps it visible in the transcript and in any summary of it;
- lets an explicit `--in` or qualified reference in the invocation override it for that one call, and says so in one line;
- takes everything about a resolved ticket — its scan roots, its bindings — from that ticket's own product, never from the context.

When a resolved ticket is outside the context, the resolver says so in `outside_context`; report it in one line rather than refusing.

---

## How a reference resolves

A reference is `[{namespace}/{product}/][{source}:]{id}`, or the ticket's web address. Resolution is implemented in `ticketlib/sources.py` and runs in this order:

1. **A web address** — anything starting `http://` or `https://` is matched against the `url.patterns` every installed source declares in its `provider.json`. The first pattern that matches wins; its `id` capture is the id, and every other capture is a coordinate. A ticket on disk whose own coordinates disagree with the address is a different ticket and is not matched.
2. **A qualified reference** — `edwire/ew-educate/ado:18585` names exactly one directory.
3. **A prefix or a bare id** — `ado:18585`, `gh:42`, `local:auth-fix`, or `18585`. Every source's own name works as a prefix, plus any alias its `provider.json` declares. The **nearest** ticket directory of that name wins: in the session context's product, then its namespace, then everywhere. **Two equally near exits 3** and lists their qualified references; the fix is to name one, never to guess.
4. **On disk nowhere** — the ticket is filed by the rules below. A bare id first takes the effective `default_source` of the scope it would be filed in.

The default namespace and product never take part in resolving an existing ticket. They only decide filing.

A reference stored inside a ticket — `parent` — resolves the same way, nearest first from **that ticket's own product**. That is why it is written short within its product and qualified across products.

An address that no pattern matches exits 1 and names the sources that accept one; it never falls through to the prefix branches, because a URL is an unambiguous statement of which ticket was meant.

**An id is validated before anything on disk is consulted.** It must be a single name — no `..`, no path separator — because it is joined onto a directory, and an id that climbed out of its own would name a namespace or product instead. With a known source it must also match that source's `id.pattern`, so `ado:not-a-number` fails at resolution rather than at the API; a bare id is only looked for under the sources whose pattern it fits.

---

## How a new ticket is filed

Two steps, in this order. Implemented in `ticketlib/filing.py`.

**1. Which products can hold it.**

- **Named** — by `--in {namespace}/{product}` or a qualified reference: only that product. Refused when it is bound to other coordinates than the ticket's, or when it cannot supply every coordinate the source needs.
- **A pasted address** — the one product whose binding matches every coordinate the address carries. Where only the namespace-level coordinate matches, that namespace's fallback product: the address itself supplies the rest. Where nothing matches, exit 1 with a hint to bind it. **Step 2 does not apply.**
- **Otherwise** — for a source with coordinates, every product whose effective binding supplies all of them; for a source with none, every product, plus the default and fallback products that may not exist yet.
- **Never** a product bound to different coordinates than the ticket's.

**2. Which of them is preferred.** One candidate is filed without preference. Otherwise the first of these that is a candidate:

1. **The session context** — its product; for a namespace-only context, that namespace's only candidate, else its default product, else its fallback product.
2. **The invocation directory** — a product whose own scan roots hold it, else a namespace whose own scan roots do. An inherited list says where the machine keeps code, not which product this directory belongs to, so it does not count.
3. **The default product** — of the `--in` namespace when one was given, else of the default namespace; then that namespace's fallback product.

When none of them decides, exit 3 lists the candidates, and the driver asks.

Every result names the product, the rule that chose it — `named`, `address`, `only-candidate`, `context`, `invocation-directory` or `default` — and why. **Report both.** A filing is never silent.

**An `--in` or a session context naming a namespace or product that does not exist exits 5** rather than filing into it, since filing would create it and a typo would become a product. The `default` namespace and every fallback product are the exception: they are created the first time a ticket lands in them.

**A fetch checks the filing it was given.** A ticket is filed before it is fetched, and only the fetch learns where it lives — an Azure DevOps id names no project. When the ticket's own coordinates contradict the product it was filed under, the fetch reports `misfiled`: each disagreeing coordinate, and `belongs_under`, the product bound to the ticket's coordinates where there is one. Report it and offer `/ticket-move`; nothing moves on its own.

---

## Exit codes

| Code | Meaning                                                                      |
| ---- | ---------------------------------------------------------------------------- |
| 0    | ok — for `drift`, also "up to date"                                          |
| 1    | error / not bound                                                            |
| 2    | `--require` unmet, **or** `drift` found the ticket moved                     |
| 3    | ambiguous reference or filing, or the source declares this capability absent |
| 5    | ticket, namespace or product not found                                       |

Exit 3 on an absent capability is structural, not advisory: the verb refuses before any provider code loads. Report it as a gap. Never substitute another source's behaviour for it, and never hand-roll the call the provider declined to make.

`--require` takes a comma-separated subset of `config, ticket_dir, ticket_json, raw, digest, plan, journal`. `config` means the source is bound where the ticket is filed: every coordinate its manifest declares is known. An unmet requirement exits 2 with a hint naming the skill that would satisfy it.

---

## Paths

**Every path in `resolve`'s output is absolute.** Neither the file tools nor a quoted shell argument expands `~`, so the resolver expands it once and no driver ever has to.

```
~/.tickets/
├── config.json                  root level: default_namespace, default_source, scan_roots
├── .credentials/{source}/       cached credentials, keyed by namespace-level coordinate — never merged, never printed
└── {namespace}/
    ├── config.json              default_product, default_source, scan_roots, sources.{source}.{namespace coordinates}
    └── {product}/
        ├── config.json          default_source, scan_roots, sources.{source}.{product coordinates}
        └── {source}/
            └── {id}/
                ├── ticket.json  source, id, title, type, native_type, state, url, last_fetched_at, coordinates
                ├── digest.md    ← ticket-digest
                ├── journal.md   ← ticket-checkpoint only; read only by ticket-resume
                ├── plan.md      ← ticket-plan
                ├── raw/         ← ticket-fetch, or the source of truth for a local store
                └── artifacts/   ← ticket-plan and ticket-implement (see ARTIFACTS.md)
```

A ticket directory holds **nothing but those six entries**. Never write a generated file directly into it.

Every `config.json` is optional; an absent one reads as empty. Objects merge key by key across levels, anything else set at an inner level replaces what an outer one set, and `[]` clears an inherited list. `default_namespace` is read from the root alone, `default_product` from its namespace alone. The resolver's `config_sources` names the file each effective value came from.

`TICKETS_HOME` overrides the tickets home, which is how a test runs against a scratch tree without touching real data.

---

## `ticket.json`

The file that keeps source-specific URL patterns out of every driver and every template.

| Key               | Notes                                                                                                                                                                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source`, `id`    | The resolved identity within its product.                                                                                                                                                                                                                                                         |
| `title`, `state`  | As the source last reported them.                                                                                                                                                                                                                                                                 |
| `type`            | One of the canonical types in `ticket-types/`.                                                                                                                                                                                                                                                    |
| `native_type`     | The source's own word for it, kept untouched alongside.                                                                                                                                                                                                                                           |
| `url`             | The ticket's web address, or **`null`** where the source has none.                                                                                                                                                                                                                                |
| `last_fetched_at` | When the snapshot was taken, in UTC.                                                                                                                                                                                                                                                              |
| `coordinates`     | Where the ticket lives upstream, recorded at fetch. They win over the binding of the product it is filed under, so re-filing never changes what it fetches from. Absent for a source with no coordinates.                                                                                         |
| `parent`          | Optional reference to a parent ticket: short when the parent is filed in the same product, qualified when it is not. Present only where the relationship exists; absent — never a fabricated value — when it does not. `ticket-types/{type}.md` says which types may carry one and what it means. |

Where the ticket is filed is **not** a key. The directory is the record of that, so a move cannot leave a stale copy.

**Read `url` and degrade to plain text when it is `null`.** A local store has no web address, and a digest that prints a broken link is worse than one that prints `#42: Cache the authorization lookup` as text.

A record may also carry a source-specific `fingerprint` (whatever that source's `drift.md` compares against) and `"incomplete": true` where a field could not be derived. An absent `title` is null — never invented.

---

## Credentials

A credential is cached under `.credentials/{source}/{key}.json`, keyed by the value of the source's namespace-level coordinate — one Azure DevOps organization's token is never handed to another. The file is created readable by its owner alone (`0600`, its directories `0700`); on Windows the user profile's own permissions protect it. It is kept out of every `config.json` because those are hand-edited and merged, and a credential must be neither.

No verb emits a credential, and no driver reads one: acquiring, caching and refreshing all happen inside the provider module.

---

## Moving

`move` tries every `parent` rewrite it owes **before** renaming anything, without writing — a dry run included — so a ticket body that cannot take one refuses the move while nothing has changed. A rename that fails, usually because a terminal or an editor holds the directory open, also changes nothing and exits 1.

Once the directory has moved, a rewrite that still fails is reported rather than raised: `result` is `moved_with_errors`, and `references_failed` names each ticket, the `parent` it should now hold, and why it could not be written. Report every one, so it can be set by hand.

**Links are reported, never rewritten** — a journal entry is never edited, and the rest is someone's writing. `links_broken_by_move` lists each relative link the move breaks, from inside the ticket or into it from another, with the `replacement` that would repair it: relative within the tickets home, an absolute `file:` address outside it. A link that still resolves is not listed. One that was broken before the move is listed under `links_already_broken` and never "repaired" into pointing somewhere new — except a link into the workspace whose target is only missing because another branch is checked out, which keeps pointing where it always did and is flagged `target_missing`. Under `raw/`, only links the move itself breaks are listed.
