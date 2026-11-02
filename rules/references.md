# References

Write every reference to a ticket, pull request, issue or commit as a **reference token** that names its kind, its ID and, when more than one repo is in play, its repo. The reader of a long conversation has several trackers and repositories in view at once; a bare `#524` can be a PR, an issue or a work item in any of them.

## Tokens

| Kind                   | Token                                     | Example                                  |
| ---------------------- | ----------------------------------------- | ---------------------------------------- |
| Azure DevOps work item | `AB#N`                                    | `AB#19078`                               |
| GitHub pull request    | `pr#N`, or `pr#N@repo`                    | `pr#524@eg-platform-devops`              |
| GitHub issue           | `issue#N`, or `issue#N@repo`              | `issue#12@eg-platform-saas`              |
| Commit                 | `commit#SHA`, or `commit#SHA@repo`        | `commit#11b2bbdf@eg-platform-saas`       |
| Local ticket           | `local:id`                                | `local:cache-authorization-lookup`       |
| Branch, tag, milestone | the name as code, plus "in repo" in prose | `` `rel/2610.1.1` `` in eg-platform-saas |

- **`@repo`** is the bare repository name. Use `owner/repo` only when two owners in play have a repository of that name.
- **`AB#N`** stands alone: a work item ID is unique within its Azure DevOps organization.
- **A SHA** is 8 characters, from `git rev-parse --short=8`. Lengthen it only when git reports 8 as ambiguous.
- **Branches, tags and milestones** stay outside the token scheme; name the repo in the sentence when the same name exists in several.

## When `@repo` may be dropped

- **In chat**, drop it only while the whole conversation has involved exactly one repository. Once a second one appears, qualify every reference from then on, including those to the first.
- **In a file** (plans, digests, journals, READMEs, any Markdown or doc), always qualify. A file is read later, without the conversation around it.

## Presentation

- **Link the token** when the URL is known or derivable — from `gh` output, the git remote, or the Azure DevOps organization: `[pr#524@eg-platform-devops](https://github.com/OWNER/eg-platform-devops/pull/524)`. Where the URL cannot be derived, write the token as plain text; a link is only ever built from a known address.
- **Title on first mention** in each message, in parentheses: `pr#524@eg-platform-devops (promote enrollment-api to QA)`. Later mentions in the same message use the token alone.
- **Several references go in a table**, one full token per row with its title and whatever status matters. Each token in a list carries its own kind and repo; a group label never stands in for them.
- **Output relayed from a skill or script** is rewritten into tokens before it reaches the user.

## Text posted to GitHub or Azure DevOps

Commit messages, pull request bodies and titles, and comments posted to GitHub or Azure DevOps use the platform's own forms, because those are what it autolinks: `#N` and `owner/repo#N` for GitHub issues and pull requests, `owner/repo@SHA` for a commit in another repository, and `AB#N` for a work item. A type or title next to the platform form is welcome.
