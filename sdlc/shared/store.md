# Store

The layout of the SDLC home and the keys of a ticket's `ticket.json`. Terms are in [`GLOSSARY.md`](../GLOSSARY.md).

## Layout

```
{sdlc home}/
    sdlc.json
    {namespace}/
        namespace.json
        {product}/
            product.json
            {source}/{id}/
                ticket.json
                raw/
                plan.md
                journal/
                artifacts/
                pulls.md
```

| Path | Holds | Format |
| --- | --- | --- |
| `sdlc.json`, `namespace.json`, `product.json` | the config of the home, a namespace and a product | `/sdlc:setup` |
| `{source}` | one of `github`, `ado`, `local` | |
| `{id}` | the source's id; a local ticket's is a slug of its title | |
| `ticket.json` | the ticket's record | below |
| `raw/` | a remote ticket: `raw.json` (the mirror) and the attachments downloaded beside it. A local ticket: `ticket.md` (the ticket file) | [providers/github.md](providers/github.md), [providers/ado.md](providers/ado.md), [adoption.md](adoption.md) |
| `plan.md` | the plan | [plan.md](plan.md) |
| `journal/` | one file per journal entry | [journal.md](journal.md) |
| `pulls.md` | the pull request record | [journal.md](journal.md) |
| `artifacts/` | probes and their captures, and spike findings | [artifacts.md](artifacts.md) |

## ticket.json

A JSON object. A writer changes its own keys and keeps every other key.

| Key | Holds | Written by |
| --- | --- | --- |
| `source` | `github`, `ado` or `local` | `fetch`; adoption for a local ticket |
| `id` | the source's id, as a string | `fetch`; adoption |
| `title` | the ticket's title | `fetch` on every refresh; adoption |
| `state` | the source's own state (`open`, `Active`); absent on a local ticket | `fetch` on every refresh |
| `type` | `user-story`, `task`, `bug`, `spike` or `tech-debt` | the model, once, at intake, adoption or `plan` |
| `url` | the ticket's URL in its source; `null` on a local ticket | `fetch` on every refresh; adoption |
| `fingerprint` | the [revision](../GLOSSARY.md): `{"rev": N}` for Azure DevOps, `{"sha256": "..."}` for GitHub | `fetch` on every refresh |
| `last_fetched_at` | UTC time of the last refresh, ISO 8601 with seconds | `fetch` |
| `coordinates` | the ticket's own coordinates, by name: `{"organization", "project"}` or `{"owner", "repository"}` | `fetch` |
| `origin` | the absolute path an adopted file was copied from; absent for text and a branch | adoption |
