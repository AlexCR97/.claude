# github — config

Read by `ticket-init`.

## What a github binding holds

Two coordinates, each at its own level — which is what makes a namespace a GitHub owner and a product one of its repositories:

| Coordinate   | Bound at  | Meaning                                                         |
| ------------ | --------- | --------------------------------------------------------------- |
| `owner`      | namespace | The user account or organization — the `owner` in `owner/name`. |
| `repository` | product   | The repository's name — the `name` in `owner/name`.             |

```json
// {namespace}/config.json
{ "sources": { "github": { "owner": "someone" } } }

// {namespace}/{product}/config.json
{ "sources": { "github": { "repository": "notes-app" } } }
```

Issue numbers are unique per repository, so a product is bound to exactly one. A GitHub Projects board is not a repository and cannot be bound: it holds issues from many repositories, and two of them can share a number.

**No token is ever stored.** That is the point of using the GitHub CLI: `gh` already holds the user's authentication, refreshes it, and knows about enterprise hosts and SSO. Copying a token out of it into this suite would create a second credential to leak, expire and forget — so this source keeps none, and there is nothing in a binding worth protecting.

## Defaults

`--repo owner/name` names both. Where the target product's namespace is already bound to an owner, `--repo name` is enough.

With no `--repo`, the init uses what the target product already inherits, and failing that asks `gh` which repository the invocation directory belongs to. Where none of them yields a repository, it stops and asks rather than guessing.

```
python "{skills}/ticket-common/ticket.py" init --source github [--in {namespace}/{product}] [--repo owner/name] [--propose]
```

A third segment would be a cross-repository reference, which a product bound to one repository cannot express — see `ticket-providers/README.md`.

Where the binding is filed when `--in` is omitted: the product already bound to exactly this repository, else a new product in the namespace already bound to the owner, else names derived from the coordinates.

## How the credential is acquired

It is not. The user runs:

```bash
gh auth login
```

once, outside this suite, and every call here goes through `gh`. Never ask for a token, never read one out of `gh`'s own config, and never pass one on a command line.

## How it is validated

Two checks, in order:

1. `gh auth status` — is the CLI signed in at all?
2. `gh api repos/{owner}/{name}` — does this account have access to _this_ repository?

They fail for different reasons and the distinction is worth keeping: the first means `gh auth login`, the second means the repository name is wrong or the account lacks access. `--propose` runs neither.

A missing `gh` is reported as a missing tool, with the install-and-login instruction. It is never worked around with a raw HTTP call.

## Report back

That the owner and repository are bound under the product named, that authentication is delegated to the GitHub CLI and nothing was stored, and that the user stays signed in through `gh` rather than through anything here.
