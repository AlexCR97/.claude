---
name: ticket-init
description: Initializes the ~/.tickets directory and binds one ticket source under a namespace and product — an Azure DevOps organization and project, a GitHub owner and repository — or creates a namespace or product with no binding. Also sets the default namespace and product, saves the default scan roots (the directories ticket-plan looks for code in), and migrates older layouts. Run it once per binding before using any other ticket-* skill — new, fetch, refine, digest, plan, implement, checkpoint, or resume.
argument-hint: "[source] [--in namespace/product] [provider options]"
---

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and every step below just says which file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill                                                        |

Never let a source-specific or type-specific fact creep back into this file — a field key, a URL, an API version, a script name, a credential command, an HTML-vs-markdown decision, or a rule that only holds for bugs or only for spikes. **If a step cannot be written without naming a particular ticket system, it belongs in `ticket-providers/{source}/`; if it cannot be written without naming a ticket type, it belongs in `ticket-types/{type}.md`. This file should only name the file to read.** A source directory may hold only some of the role files; treat each as present-or-absent independently, and never substitute another source's or another type's module for a missing one.

No `allowed-tools` here: this skill writes config and runs a migration, so an allowlist narrow enough to be meaningful would also block the work.

---

## Purpose

Sets up where tickets are kept and where they come from. A **binding** records one source's coordinates on a namespace and a product — which organization, which project — so that tickets fetched from there are filed together, apart from every other body of work. This skill resolves which source, proposes where its binding is filed, acquires and validates whatever credential it needs, and writes the binding.

It also records three things that shape every later skill: the **default namespace and product**, where a new ticket goes when nothing else decides; `default_source`, so a bare id resolves without a prefix; and the **default scan roots**, so `ticket-plan` knows where to look for code. Namespace, product, binding, scan root and every other term here mean exactly what `ticket-common/GLOSSARY.md` says.

The config lives in the user's home directory, so it is shared across every repository. The other `ticket-*` skills read it automatically.

Run it once per binding. Running it again for a binding that already exists is a re-initialization, and it asks first. It can also create a namespace or product with no binding at all — a side project with only local tickets.

**Read `ticket-providers/{source}/config.md`** for what that source binds, at which level, what defaults it applies, how its credential is acquired, and how it is validated. This file deliberately holds none of that: there is no default organization here, no credential command, and no coordinate flag.

---

## Input

```
/ticket-init [{source}] [--in {namespace}/{product}] [{provider options}]
/ticket-init --in {namespace}[/{product}]
```

- `{source}` — which source to bind. When omitted, see step 3.
- `--in` — the product to bind it under, or with no source, the namespace or product to create. When omitted for a binding, step 4 proposes one.
- `{provider options}` — anything that source's `config.md` documents. **Pass through only what the user explicitly supplied**; every omitted flag keeps what the product already inherits, then that source's own default.

---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Enumerate what exists

```bash
python "{skills}/ticket-common/ticket.py" sources
python "{skills}/ticket-common/ticket.py" namespaces
```

The first is the list of what can be bound, with each source's capabilities and the levels its coordinates are bound at. The second is every namespace and product already here, with their bindings. **Never assume a fixed set of either** — sources are discovered by glob, and namespaces and products are whatever directories exist.

If either exits 4, the tickets home still holds an older layout; step 2 migrates it, then run step 1 again.

### 2. Run the migration check

**Every invocation, whatever is being set up.** It runs first because every later step writes the current layout, and the front door refuses to while an older one is on disk. Data from an older layout is migrated by a script, because renaming directories and rewriting config are the operations where a half-completed pass is worst, and neither requires any judgement.

Dry-run it first:

```bash
python "{skills}/ticket-common/ticket.py" migrate --dry-run
```

- `result` is `nothing_to_migrate` → say nothing and continue to step 3.
- Otherwise → **show the report and ask** before running it for real. Name how many tickets would move, the product each source's tickets would be filed under, the bindings and credential that would move, and every link it would rewrite or leave broken.

**A source whose tickets would land in `default/default`** — one with no coordinates to file them by — is worth asking about: "Every `{source}` ticket would be filed under `default/default`. File them under another product instead?" Offer the products the dry run would create. For each answer, re-run the dry run with `--map {source}={namespace}/{product}` and show it again.

On approval, run the same verb without `--dry-run`, passing the same `--map` flags, and report what it did. Say that each ticket directory was renamed in place, not copied, and name any link reported as broken so the user can fix it by hand.

It never merges into an existing destination and never overwrites an existing credential — either is reported as skipped, and a skipped ticket leaves its old directory in place and the migration unfinished. Do not work around a skip by hand: a partial merge of two plan histories is unrecoverable.

### 3. Resolve what is being set up

- **A source was given** → a binding. Continue to step 4.
- **Only `--in` was given** → a namespace or product with no binding:

  ```bash
  python "{skills}/ticket-common/ticket.py" init --in "{namespace}[/{product}]"
  ```

  Report what it created, then skip to [step 7](#7-set-the-default-namespace-and-product).

- **Neither** → list the installed sources with their `kind` and capabilities, and **ask** which to bind, or whether to create a namespace or product with no binding. Where exactly one source is installed, propose it, and say so. Do not treat whichever source is alphabetically first or historically usual as the answer.

### 4. Propose where the binding goes

**Read `ticket-providers/{source}/config.md` first** — it names the coordinates this source binds, which level each one belongs to, and which options set them.

```bash
python "{skills}/ticket-common/ticket.py" init --source {source} [--in "{namespace}/{product}"] [{provider options}] --propose
```

It validates nothing and writes nothing. It reports the `coordinates` the init would bind, the `product` they would be filed under, whether that product and its namespace exist yet, whether it is `already_bound` to exactly these coordinates, which values came from a default or were inherited, and any `problems`.

Show the coordinates and the product, and ask:

> Bind {source} {coordinates} under `{product}`? Or name another namespace and product.

The proposed names are derived from the coordinates, so they are usually what the user wants — but they are directory names the user has to live with, so confirm them. Where the user names others, run `--propose` again with `--in` to check them.

- **`problems` is not empty** → show each and ask for another namespace or product. Never bind over a problem: each one — a duplicate binding, a namespace already bound to other coordinates, a fallback product being bound — would file some address in two places or in the wrong one.
- **`already_bound` is true** → this is a re-initialization. Ask `Re-initialize {product}? [y/N]` — it re-acquires and re-validates the credential. If the user declines, skip to [step 7](#7-set-the-default-namespace-and-product): the binding stays as it is, but the defaults and scan roots can still be updated.

### 5. Run the init

```bash
python "{skills}/ticket-common/ticket.py" init --source {source} --in "{namespace}/{product}" [{provider options}]
```

Always pass the confirmed product with `--in`, so what is written is exactly what the user agreed to in step 4. Pass a provider option only for a value the user explicitly supplied.

Never ask the user for a credential, and never run a credential command yourself. Credential handling belongs to the provider module, which is why this skill has no way to see one.

Wait for the script to complete. If it exits with a non-zero code, report the error output verbatim and stop — do not write or modify any file yourself.

### 6. Note what the init wrote

The output names the `namespace_config` and `product_config` each coordinate was written to, the effective `config`, and `config_sources` — which file each value came from. Keep them for the report in step 9.

### 7. Set the default namespace and product

Every invocation. Read the current defaults:

```bash
python "{skills}/ticket-common/ticket.py" defaults
```

Where none is configured (`configured.default_namespace` is null) and this run created or bound a namespace and product, propose them:

> New tickets that nothing else places go to `default/default`. Make `{namespace}/{product}` the default instead?

Where defaults are configured, show them and offer to keep them:

> Default namespace and product: `edwire/ew-educate`. Keep these, or name others?

Wait for the answer, then save exactly what the user named:

```bash
python "{skills}/ticket-common/ticket.py" defaults --namespace {namespace} --product "{namespace}/{product}"
```

`--namespace` sets the machine's default namespace; `--product` sets that namespace's default product, and may be given alone to set another namespace's default without making it the machine's. `default` unsets either. Skip the call only when the user kept what is there.

The defaults only ever decide where a **new** ticket is filed — never which existing ticket a reference means — so say that in one line when they change.

### 8. Record the default scan roots

The default scan roots are the directories `ticket-plan` starts every discovery from: worktrees of repositories, or directories holding several repositories. A ticket whose code is reachable from one needs no directory named at plan time. They can be saved at the root, on a namespace or on a product, and a plan uses the nearest level that sets them — so an EdWire plan never scans personal repositories.

Ask about the level this run set up: the binding's **namespace** by default, or the product the user asks for; the **root** when this run bound nothing. Read the current list there:

```bash
python "{skills}/ticket-common/ticket.py" scan-roots [--in "{namespace}[/{product}]"]
```

`own` is what that level sets; `scan_roots` is the effective list and `scan_roots_from` the file it came from. Then ask:

> Which directories should ticket-plan look for code in for `{level}`? List each repository's worktree, or a directory holding several repositories. Say "none" for an empty list, or "inherit" to use `{scan_roots_from level}`'s.

Where the level already sets a list, show it and offer to keep it:

> Default scan roots for `edwire`: `C:\src\billing-api`, `C:\src\contracts`. Keep these, or give the full list to replace them?

Wait for the answer. Save exactly the directories the user listed; never add one they did not name, such as the invocation directory:

```bash
python "{skills}/ticket-common/ticket.py" scan-roots [--in "{namespace}[/{product}]"] --set ["{dir}" ...]
```

`--set` with no directory saves an empty list, which **clears** an inherited one at this level — run it that way only when the user said "none". Skip the call when the user kept the existing list or said "inherit". A non-zero exit names the directory that does not exist and saves nothing; show it and ask again.

### 9. Report the result

On a binding:

> `{source}` bound under `{product}`. {Coordinates} written to `{namespace_config}` and `{product_config}`.
> You can now run `/ticket-fetch {source}:{id}` to pull a ticket down.

Also state:

- **Which values were used, and which came from a default or were inherited** — so a default is never applied silently. Both lists are in the init's own output.
- **Whether `default_source` was set**, and to what. The front door sets it only when the root had none; an init for a second source **never silently repoints it**. Where a default already existed, say which source it is and that bare ids not on disk still resolve there.
- **The default namespace and product**, and whether they changed.
- Anything the source's `config.md` says is worth reporting — a credential's expiry, how it refreshes, what the user must keep doing to stay signed in.
- **The default scan roots as saved**, at which level, or that the list is empty and `ticket-plan` will fall back to its invocation directory.

Where the source offers `new` rather than `fetch`, point at `/ticket-new` instead; the capabilities in step 1's output say which.

Where re-initialization was declined in step 4, or this run only created a namespace or product, report only what did change: what was created, the defaults, and the scan roots.

On failure, report the error output from the script verbatim and stop.

---

## Constraints

- Never write or modify a config file directly — always delegate to the front door
- Never print a credential value in chat, and never paste one into a command
- Never ask the user for a credential of any kind — the provider acquires and refreshes it
- Never run a credential command yourself — that belongs to the provider module
- Never pass a provider option unless the user supplied that value — let the product's inherited binding and the source's own defaults apply
- Never assume which sources, namespaces or products exist; enumerate them
- Never bind without confirming the namespace and product it goes under, and never over a reported problem
- Never silently repoint `default_source` — report what it is, and change it only when there was none
- Run the migration check on every invocation and before anything else, and never run the migration for real without showing the dry run and asking
- Ask about the default namespace and product, and about the default scan roots, on every invocation, including one where re-initialization was declined. Save only what the user named, and an empty scan-roots list only when they said "none"
- Do not proceed past a non-zero exit code
