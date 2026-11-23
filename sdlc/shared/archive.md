# Archive

The format of an archive: the zip `archive export` writes and `archive import` reads. Terms are in [`GLOSSARY.md`](../GLOSSARY.md); the layout it carries is [store.md](store.md).

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
