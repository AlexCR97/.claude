# github — new

A **recipe**. Read by `ticket-create`. Creating an issue writes to GitHub, and it outlives the session and is visible to everyone who can see the repository, so the skill's own gate applies first: show everything, and take an explicit yes. This file is only how to build and send it. The commands are examples, not an allowlist: use whatever `gh` call the work needs.

`{owner}` and `{repository}` are the `coordinates` the resolver reports for the product the ticket will be filed under. Always pass `--repo {owner}/{repository}`.

## What is sent

| Field               | Sent as                                                                                                                                  |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Title               | `--title`                                                                                                                                |
| Description         | the body — markdown                                                                                                                      |
| Acceptance criteria | appended to the body under `## Acceptance Criteria`, because an issue has no field for them (`schema.md`)                                |
| Labels              | `--label`, repeatable, plus the label for the type (`types.md`). A `task` has none and is created unlabelled, which reads back as `task` |

Assignee, milestone and project are out of scope. So is a parent: an issue has no typed parent link, so refuse `--parent` here.

## 1. Show it all, and take a yes

Show the product it will be filed under, the repository, the title, the type, the labels that will be applied and the full body. Let the user correct any of it; show it again after each correction. Only a plain yes is a yes.

`gh issue create` fails for a label the repository does not have. List them first (`gh label list --repo {owner}/{repository} --json name`), and for one that is missing say so before the yes: creating it is a second write.

## 2. Create

Write the body to a scratch file outside the ticket directory:

```bash
gh issue create --repo {owner}/{repository} --title "…" --body-file {file} --label "…"
```

It prints the new issue's address; the number is its last segment.

## 3. File it

The number is only known now, so the issue is fetched and filed like any other, with the same coordinates:

```bash
python "{skills}/ticket-common/ticket.py" fetch github:{number} --in {namespace}/{product}
```

Where the fetch's `type` is not the type that was asked for, run `ticket.py resolve github:{number} --type {type}`, which records it.
