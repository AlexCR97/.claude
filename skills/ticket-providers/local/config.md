# local — config

Read by `ticket-init`.

## What `local/config.json` holds

```json
{}
```

Nothing. There is no service to connect to, no coordinates to record, and **no credential of any kind**.

The file is still written, and that is deliberate: `on_disk.config` is how every driver distinguishes "set up" from "never set up", and a store that needs no credential still has to answer that question. An empty object is the honest answer.

## What init actually does

Creates the store directory and writes the empty config. It makes no network call, runs no external command, and asks the user for nothing.

```
python "{skills}/ticket-common/ticket.py" init --source local
```

There are no provider options.

## What to report afterwards

That the store is local files, that it needs no credential and will never expire, and that tickets here are created with `/ticket-new` rather than fetched — this source has no `fetch`.
