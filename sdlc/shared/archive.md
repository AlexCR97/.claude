# Archive

The format of an archive, the zip `archive export` writes, and how `archive import` merges one into the SDLC home. Terms are in [`GLOSSARY.md`](../GLOSSARY.md); the layout it carries is [store.md](store.md).

## Scope

The scope is what `archive export` is given, and decides what the zip holds:

| Argument                | Kind        | Holds                                                                                   |
| ----------------------- | ----------- | --------------------------------------------------------------------------------------- |
| none                    | `home`      | `sdlc.json` and every namespace directory                                               |
| `{namespace}`           | `namespace` | `sdlc.json` and the namespace directory                                                 |
| `{namespace}/{product}` | `product`   | `sdlc.json`, the namespace's `namespace.json` and the product directory                 |
| a ticket reference      | `ticket`    | `sdlc.json`, the `namespace.json` and `product.json` above it, and the ticket directory |

- **A directory travels whole**: every file under it, as it sits in the home. A config file above the scope travels so the scope's effective config travels with it; one that does not exist is left out.
- **A bare name is a namespace when one exists**, else a ticket reference. A name that is both is ambiguous (exit 3): name the ticket as `source:id` or by its qualified reference.
- A ticket reference resolves as `resolve` resolves an existing ticket, nearest the `--context` first. One on disk nowhere is an error: export never files a ticket.

## Zip

- **Entries are paths relative to the SDLC home, with `/`**: `sdlc.json`, `acme/namespace.json`, `acme/billing-app/github/1234/plan.md`. Files only; an empty directory does not travel.
- **`manifest.json` at the root**, beside `sdlc.json`. No namespace can take the name: a namespace name has no `.`.
- **Named `sdlc-{scope}-{YYYY-MM-DD}T{HH-MM-SS}Z.zip`**, the scope being `home` or its reference slugged (`acme-billing-app-github-1234`), the time the UTC time of export. Written in the invocation directory, or where `--out` says: a file, or an existing directory to write the named zip in.
- **Never overwrites a file, and never lands inside the SDLC home**, where the next export would carry it.

## Manifest

```json
{
  "format": "sdlc-archive",
  "version": 1,
  "scope": { "kind": "ticket", "ref": "acme/billing-app/github:1234" },
  "created_at": "2026-11-23T14:05:09Z",
  "source_home": "C:\\Users\\dev\\.sdlc",
  "tickets": ["acme/billing-app/github:1234"]
}
```

| Key           | Holds                                                                                                                                |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `format`      | always `sdlc-archive`                                                                                                                |
| `version`     | the format's version, an integer. A reader refuses a version it does not know                                                        |
| `scope`       | `kind`: `home`, `namespace`, `product` or `ticket`. `ref`: `null`, the namespace, `{namespace}/{product}` or the qualified reference |
| `created_at`  | UTC time of export, ISO 8601 with seconds                                                                                            |
| `source_home` | the absolute path of the SDLC home exported from, on the machine it was exported from                                                |
| `tickets`     | the qualified reference of every ticket directory in the zip, sorted by product, source, then id                                     |

A change to any key's meaning, or a new key a reader must understand, raises `version`.

## Import

`archive import <zip>` reads the archive and prints the report as JSON; it writes nothing. `archive import <zip> --apply --digest <digest> [--take-theirs <ticket>]... [--keep-mine <ticket>]...` writes the merge that report described.

- **Refused before anything is written**: no `manifest.json`, a `format` other than `sdlc-archive`, a `version` this reader does not know, a `created_at` that is not a UTC time, or an entry outside the layout of a home (an absolute path, `..`, `\`, a name that is not a slug).
- **Apply re-checks the report.** The digest covers the report and every file the merge reads; a home or archive changed since the report is refused (exit 1), and so is a file that appeared where an add would land. Every ticket under `conflicts` takes exactly one `--take-theirs` or `--keep-mine`, by its qualified reference; a missing, extra or double choice is refused.

### Merge rules

Nothing in the home is deleted. A file identical on both sides is left alone.

| What differs                                         | Rule                                                                                                                                                                                                                                               |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A file or ticket the home lacks                      | Added.                                                                                                                                                                                                                                             |
| A journal entry                                      | A union by file name. An entry of the same name keeps the home's copy.                                                                                                                                                                             |
| A remote ticket's mirror (`raw/`)                    | Taken whole when the archive's revision is newer: a higher `rev`, else, for a hash, a later `last_fetched_at`. Otherwise the home's mirror stays untouched.                                                                                        |
| `ticket.json`                                        | The mirror's keys (`title`, `state`, `url`, `fingerprint`, `last_fetched_at`, `coordinates`) follow the mirror kept. `unposted_journal` is the union of both sides. A key only the archive has is added. A key both set differently is a conflict. |
| `plan.md`, `pulls.md`, a local ticket's `raw/` files | A conflict.                                                                                                                                                                                                                                        |
| A conflict                                           | Asked once per ticket: `--take-theirs` writes the archive's side of every conflicting file, `--keep-mine` keeps the home's.                                                                                                                        |
| Any other file, such as an artifact                  | Both kept: the archive's copy is written beside the home's as `{stem}.imported-{created_at}{suffix}`, the time with `-` for `:`.                                                                                                                   |
| A config file                                        | Merged key by key, the home's value winning where both set one: bindings (`sources`) and defaults add what is missing; `protected_branches` and `sensitive` are a union.                                                                           |
| `scan_roots`, `worktree_root`                        | Never imported, into an existing config file or a new one: they name directories on the other machine.                                                                                                                                             |

### Report

| Key                       | Holds                                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------ |
| `adds`                    | the files written new, relative to the home                                                            |
| `new_tickets`             | the qualified reference of every ticket the home lacks                                                 |
| `kept_mine`               | `path` and `reason` of each difference the home's side wins without asking                             |
| `kept_both`               | `path` of each differing file and `as`, the name the archive's copy is written under                   |
| `mirrors`                 | each remote ticket whose mirrors differ: `ticket`, `mine` and `theirs` (the fingerprints), and `taken` |
| `merges`                  | `path` and `keys` of each `ticket.json` and config file merged without asking                          |
| `not_imported`            | `path` and `keys` of each config file whose `scan_roots` or `worktree_root` stay behind                |
| `missing_workspace_paths` | each ticket whose archived plan names workspace paths that do not exist here: `ticket` and `paths`     |
| `conflicts`               | each ticket to ask about: `ticket` and `files`, relative to the ticket directory                       |
| `digest`                  | what `--apply` must be given                                                                           |

With `--apply`, the same keys plus `applied: true`.
