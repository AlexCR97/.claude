# Scripts are for mechanical work only

A ticket script exists only where the result must be byte-identical every run: downloading a ticket into `raw/`, creating a local ticket, hashing a file, resolving a layout, moving a directory. Everything that talks to a ticket system's write API, and every judgement about what changed, is a **recipe**: a role file telling the agent how to use the source's own CLI (`gh`, `az`), with its commands as examples rather than an allowlist.

This replaces scripts that wrapped each provider operation behind a fixed set of flags. They limited what the skills could do: `ticket-fetch` rejected any form of a GitHub address its regexes did not list, and the Azure DevOps update script had no flag for tags, which are one `;`-separated string and need a read before a write. A recipe handles both without new code.

What shipped:

- **Remote `new`, `update` and `drift` for GitHub and Azure DevOps are recipes.** Azure DevOps writes are a JSON Patch through `az rest` that opens with `test /rev`, so an edit made since the snapshot is rejected rather than overwritten. The `azure-devops` extension is a prerequisite that `init` checks.
- **Input is normalized by the agent.** `resolve` takes only a canonical or qualified reference plus `--coordinate name=value`. The first step of `ticket-fetch`, `ticket-plan` and `ticket-digest` reads whatever the user gave, using the source's `links.md`. `url.patterns` and `url.refused` are gone from `provider.json`.
- **`az` and `gh` own every credential.** The token cache, the HTTP layer and the `update` and `auth-status` verbs are deleted, and the rule is that nothing prints or reads a token. Fetching goes through `az rest`.
- **Gates are prose in each writing skill**: an explicit yes after a before and after, a drift check against the live ticket, and the revision guard. The protected-branch guard stays a script (ADR 0001).
- A capability flag in `provider.json` now means "this source has a role file for it", whether that file is a contract or a recipe. The on-disk layout is unchanged, so existing tickets need no migration.

The cost is that a gate which was code is now an instruction, and a skipped one is not caught by a test. Accepted, because the earlier gates were enforced only for the operations the scripts happened to support.
