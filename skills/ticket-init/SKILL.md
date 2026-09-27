---
name: ticket-init
description: Binds a ticket source — an Azure DevOps organization and project, a GitHub owner and repository — under a namespace and product in ~/.tickets, or creates an unbound namespace or product. Also sets the default namespace, product and scan roots. Run once per binding, before any other ticket-* skill.
argument-hint: "[source] [--in namespace[/product]] [provider-options]"
allowed-tools: Read Bash(python *ticket.py:*)
---

Sets up where tickets are kept and where they come from: binds one source's coordinates to a namespace and product, or creates a namespace or product with no binding, then records what every later skill reads — the default namespace and product, `default_source`, and the default scan roots `ticket-plan` starts from. The config lives in `~/.tickets`, shared across every repository. Every term here means what `ticket-common/GLOSSARY.md` says.

End state: the binding validated and written through `ticket.py`, or the namespace or product created; the defaults and scan roots saved exactly as the user named them; and a report of every value that came from a default or was inherited.

This skill is a **driver**: it contains no field names, URLs, API versions, credential commands, markup dialects, or type-specific rules of its own. Everything specific lives alongside it in three directories, and each step names the file to read.

| Directory                    | Contains                                                                                                          | Read                                                                          |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ticket-common/`             | the resolver (`ticket.py`) and the shared contracts — `RESOLUTION.md`, `ARTIFACTS.md`, `STATUS.md`, `GLOSSARY.md` | as each step names                                                            |
| `ticket-providers/{source}/` | everything specific to where the ticket came from                                                                 | only the **resolved** source's directory, and only the role file a step names |
| `ticket-types/{type}.md`     | everything specific to what shape the work is                                                                     | not read by this skill                                                        |

A fact that needs a particular ticket system belongs in `ticket-providers/{source}/`, and one that needs a ticket type belongs in `ticket-types/{type}.md` — never in this file.

---

## Parameters

- **`[source]`** — which source to bind. Step 2 resolves `{source}` from it, or asks when it is absent.
- **`[--in namespace[/product]]`** — the product to bind `[source]` under, or, with no `[source]`, the namespace or product to create. Step 3 proposes one when it is absent for a binding.
- **`[provider-options]`** — any option the source's `config.md` documents. Pass through only what the user supplied; every omitted option keeps what the product already inherits, then the source's own default.

---

## Ground rules

1. **Write config only through `ticket.py`.** Never write or modify a config file directly.
2. **Never handle a credential.** Never ask for one, print one, paste one into a command, or run a credential command — the provider acquires and refreshes it.
3. **Pass a provider option only when the user supplied its value.** Every omitted option keeps what the product inherits, then the source's own default.
4. **Enumerate; never assume.** Take the sources, namespaces and products from Step 1's output, never from a fixed list.
5. **Confirm before binding.** Never bind without confirming the namespace and product, and never over a reported problem.
6. **Never silently repoint `default_source`.** Report what it is; the front door changes it only when there was none.
7. **Ask about the defaults and the scan roots on every run**, including one where re-initialization was declined. Save only what the user named, and an empty scan-roots list only when they said "none".
8. **Stop on a non-zero exit.** The one exception is Step 7's `scan-roots --set`, which names the missing directory and asks again.

---

## Execution Steps

### Step 1 — Enumerate what exists

```bash
python "{skills}/ticket-common/ticket.py" sources
python "{skills}/ticket-common/ticket.py" namespaces
```

The first is the list of what can be bound, with each source's capabilities and the levels its coordinates are bound at. The second is every namespace and product already here, with their bindings. **Never assume a fixed set of either** — sources are discovered by glob, and namespaces and products are whatever directories exist.

### Step 2 — Resolve what is being set up

- **A source was given** → a binding. Continue to Step 3.
- **Only `--in` was given** → a namespace or product with no binding. The explicit `--in` is the approval; create only what it names:

  ```bash
  python "{skills}/ticket-common/ticket.py" init --in "namespace[/product]"
  ```

  Report what it created, then skip to Step 6.

- **Neither** → list the installed sources with their `kind` and capabilities, and ask which to bind, or whether to create a namespace or product with no binding. Where exactly one source is installed, propose it, and say so. Do not treat whichever source is alphabetically first or historically usual as the answer.

### Step 3 — Propose where the binding goes

**Read `ticket-providers/{source}/config.md` first** — it names the coordinates this source binds, which level each one belongs to, and which options set them.

```bash
python "{skills}/ticket-common/ticket.py" init --source {source} [--in "{namespace}/{product}"] [provider-options] --propose
```

It validates nothing and writes nothing. It reports the `coordinates` the init would bind, the `product` they would be filed under, whether that product and its namespace exist yet, whether it is `already_bound` to exactly these coordinates, which values came from a default or were inherited, and any `problems`.

- **`problems` is not empty** → show each and ask for another namespace or product. Never bind over a problem: each one — a duplicate binding, a namespace already bound to other coordinates, a fallback product being bound — would file some address in two places or in the wrong one.
- **`already_bound` is true** → this is a re-initialization, which re-acquires and re-validates the credential. Ask whether to re-initialize `{product}`, defaulting to no. On yes, continue to Step 4. On no, skip to Step 6: the binding stays as it is, but the defaults and scan roots can still change.
- **Otherwise** → show the coordinates and the product, and ask whether to bind `{source}` there or under another namespace and product. The proposed names are derived from the coordinates, so they are usually what the user wants — but they are directory names the user has to live with, so confirm them.
  - **Confirmed** → continue to Step 4.
  - **Another namespace and product named** → run `--propose` again with `--in` set to them, and return to the start of this list.
  - **Declined** → bind nothing, and skip to Step 6.

### Step 4 — Run the init

```bash
python "{skills}/ticket-common/ticket.py" init --source {source} --in "{namespace}/{product}" [provider-options]
```

Always pass the confirmed product with `--in`, so what is written is exactly what the user agreed to in Step 3. Pass a provider option only for a value the user explicitly supplied.

Never ask the user for a credential, and never run a credential command. Credential handling belongs to the provider module, which is why this skill has no way to see one.

On a non-zero exit, report the error output verbatim and stop. Write no file.

### Step 5 — Note what the init wrote

The output names the `namespace_config` and `product_config` each coordinate was written to, the effective `config`, and `config_sources` — which file each value came from. Keep them for the report in Step 8.

### Step 6 — Set the default namespace and product

Every invocation. Read the current defaults:

```bash
python "{skills}/ticket-common/ticket.py" defaults
```

- **None configured (`configured.default_namespace` is null), and this run created or bound a namespace and product** → say that new tickets nothing else places go to `default/default`, and propose `{namespace}/{product}` instead.
- **None configured, and this run set up no product** → say that new tickets go to `default/default`, and ask whether to name a default.
- **Defaults configured** → show them, and ask whether to keep them or name others.

Wait for the answer, then save exactly what the user named:

```bash
python "{skills}/ticket-common/ticket.py" defaults --namespace {namespace} --product "{namespace}/{product}"
```

`--namespace` sets the machine's default namespace; `--product` sets that namespace's default product, and may be given alone to set another namespace's default without making it the machine's. `default` unsets either. Skip the call only when the user kept what is there.

The defaults only ever decide where a **new** ticket is filed — never which existing ticket a reference means — so say that in one line when they change.

### Step 7 — Record the default scan roots

The default scan roots are where `ticket-plan` starts discovery, saved in the root `config.json`, a namespace's or a product's — `ticket-common/GLOSSARY.md` → *Default scan roots*.

Ask about the level this run set up: the binding's namespace by default, or the product the user asks for; the root `config.json` when this run bound nothing. Read the current list there:

```bash
python "{skills}/ticket-common/ticket.py" scan-roots [--in "{namespace}[/{product}]"]
```

`own` is what that level sets; `scan_roots` is the effective list and `scan_roots_from` the file it came from.

- **The level sets no list** → ask which directories `ticket-plan` should look for code in at that level: each repository's worktree, or a directory holding several repositories. "none" saves an empty list; "inherit" keeps the list from `scan_roots_from`.
- **The level already sets a list** → show it, and ask whether to keep it or give the full list that replaces it.

Wait for the answer. Save exactly the directories the user listed; never add one they did not name, such as the invocation directory:

```bash
python "{skills}/ticket-common/ticket.py" scan-roots [--in "{namespace}[/{product}]"] --set ["{dir}" ...]
```

`--set` with no directory saves an empty list, which **clears** an inherited one at this level — run it that way only when the user said "none". Skip the call when the user kept the existing list or said "inherit". A non-zero exit names the directory that does not exist and saves nothing; show it and ask again.

### Step 8 — Report the result

On a binding, report that `{source}` is bound under `{product}`, and name the coordinates and the `namespace_config` and `product_config` they were written to. Point at `/ticket-fetch` as the next step, or at `/ticket-new` where the source offers `new` rather than `fetch` — Step 1's capabilities say which. Also report:

- **Which values were used, and which came from a default or were inherited** — so a default is never applied silently. Both lists are in the init's own output.
- **Whether `default_source` was set**, and to what. The front door sets it only when the root had none; an init for a second source **never silently repoints it**. Where a default already existed, say which source it is and that bare ids not on disk still resolve there.
- **The default namespace and product**, and whether they changed.
- Anything the source's `config.md` says is worth reporting — a credential's expiry, how it refreshes, what the user must keep doing to stay signed in.
- **The default scan roots as saved**, at which level, or that the list is empty and `ticket-plan` will fall back to its invocation directory.

Where the binding or re-initialization was declined in Step 3, or this run only created a namespace or product, report only what did change: what was created, the defaults, and the scan roots.
