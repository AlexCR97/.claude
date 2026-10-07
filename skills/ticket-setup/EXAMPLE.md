# Examples — ticket-setup

`/ticket-setup [source] [--in namespace[/product]] [provider-options]`

Every argument is optional: without a source it asks what to set up, and without `--in` it proposes where the binding goes.

| Invocation                                   | Sets up                                                             |
| -------------------------------------------- | ------------------------------------------------------------------- |
| `/ticket-setup`                              | asks which source to bind, or which namespace or product to create  |
| `/ticket-setup ado`                          | a binding for that source, under the product it proposes            |
| `/ticket-setup ado --in acme/web`            | a binding for that source under `acme/web`                          |
| `/ticket-setup ado --org acme --project Web` | a binding to exactly those coordinates, per the source's options    |
| `/ticket-setup --in personal/side-project`   | a namespace and product with no binding; a bare namespace works too |
