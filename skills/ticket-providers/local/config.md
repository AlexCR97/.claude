# local — config

Read by `ticket-setup`.

## What a local binding holds

Nothing. `provider.json` declares no coordinates: there is no service to connect to, nothing upstream to locate a ticket in, and **no credential of any kind**.

A source with no coordinates is usable in **every** product without an init, so a local ticket can be created under any namespace and product the moment it exists — a side project that has nothing upstream at all is a product with only local tickets.

## What init actually does

With `--in`, it creates that product if it does not exist. Without, there is nothing to do. It makes no network call, runs no external command, writes no config, and asks the user for nothing.

```
python "{skills}/ticket-common/ticket.py" init --source local [--in {namespace}/{product}]
```

There are no provider options. `init --in {namespace}/{product}` with no source creates a product just the same.

## What to report afterwards

That the store is local files, that it needs no credential and will never expire, and that tickets here are created with `/ticket-create` rather than fetched — this source has no `fetch`.
