# github — update

A **recipe**. Read by `ticket-update`. Changing an issue writes to GitHub, and the skill's own gates apply first: the drift check (`drift.md`), a before and after, and an explicit yes. This file is only how to write. The commands are examples, not an allowlist: use whatever `gh` call the change needs.

`{owner}` and `{repository}` are the `coordinates` the resolver reports. Always pass `--repo {owner}/{repository}`; never rely on the repository the invocation directory happens to belong to.

## What can change

| Field               | How                                                                                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Title               | `gh issue edit {number} --repo {owner}/{repository} --title "…"`                                                                                        |
| Description         | the part of the body before the acceptance criteria — see [The body](#the-body)                                                                         |
| Acceptance criteria | the `## Acceptance Criteria` section of the body — an issue has no field for them (`schema.md`)                                                         |
| State               | `gh issue close {number} --repo …` (optionally `--reason "not planned"`), or `gh issue reopen {number} --repo …` — this source has only open and closed |
| Labels              | `gh issue edit {number} --repo … --add-label "…" --remove-label "…"`, repeatable                                                                        |

Comments are not changed here. Assignee, milestone and project are out of scope.

## The body

An issue's body is one markdown string. The acceptance criteria are the section under an `## Acceptance Criteria` heading (two or three `#`), ending at the next heading of the same or a higher level; the description is what precedes it and whatever follows the section is carried through untouched.

To change the description or the criteria, build the **whole new body** from the snapshot's `issue.body`, replacing only the part that changed, write it to a scratch file outside the ticket directory, and send it:

```bash
gh issue edit {number} --repo {owner}/{repository} --body-file {file}
```

Where there is no criteria section yet, a new one goes at the end of the description, before anything that followed it. Show the user the part that changed as a before and after, not the whole body.

## Labels

Compare case-insensitively; adding a label the issue already has changes nothing. `--add-label` fails for a label the repository does not have. Creating one is a second write, so say so and ask before running `gh label create`. A label decides the ticket's type (`types.md`), so a label change can change the type the next fetch records; say so when a requested label is one of those.

## There is no revision guard

GitHub offers no way to make an edit conditional on the issue not having moved. So run the drift check **immediately before the write**, and compare `updated_at` once more if time has passed since: that narrows the window, and a very small one remains. Say so only if the check shows the issue moved in between.
