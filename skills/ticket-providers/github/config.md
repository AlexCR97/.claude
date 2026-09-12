# github — config

Read by `ticket-init`.

## What `github/config.json` holds

```json
{
  "repository": "owner/name"
}
```

One key. **No token is ever stored.**

That is the point of using the GitHub CLI: `gh` already holds the user's authentication, refreshes it, and knows about enterprise hosts and SSO. Copying a token out of it into another config file would create a second credential to leak, expire and forget — so this source keeps none, and there is nothing in its config worth protecting.

## Defaults

There is no default repository. If `--repo` is not given, the init asks `gh` which repository the current directory belongs to, and uses that if there is one. Where neither yields a repository, it stops and asks rather than guessing.

```
python "{skills}/ticket-common/ticket.py" init --source github [--repo owner/name]
```

The value must be exactly `owner/name`. A third segment would be a cross-repository reference, which this provider's layout cannot express — see `ticket-providers/README.md`.

## How the credential is acquired

It is not. The user runs:

```bash
gh auth login
```

once, outside this suite, and every call here goes through `gh`. Never ask for a token, never read one out of `gh`'s own config, and never pass one on a command line.

## How it is validated

Two checks, in order:

1. `gh auth status` — is the CLI signed in at all?
2. `gh api repos/{owner}/{name}` — does this account have access to *this* repository?

They fail for different reasons and the distinction is worth keeping: the first means `gh auth login`, the second means the repository name is wrong or the account lacks access.

A missing `gh` is reported as a missing tool, with the install-and-login instruction. It is never worked around with a raw HTTP call.

## Report back

That the repository is configured, that authentication is delegated to the GitHub CLI and nothing was stored, and that the user stays signed in through `gh` rather than through anything here.
