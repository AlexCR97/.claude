---
name: ctl-github-pull-request
description: Creates (or updates if one already exists) a pull request from the current branch into the main branch, with details derived from commits ahead of main.
---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Gather context

Run these commands in parallel to understand the current state:

- `git branch --show-current` — get the current branch name
- `git remote -v` — confirm a remote exists
- `git log main..HEAD --oneline` — list commits ahead of main
- `git diff main...HEAD` — see all changes relative to main
- `gh pr list --head <current-branch> --json number,title,url,state` — check if a PR already exists for this branch

If the current branch **is** `main` or `master`, inform the user that a PR cannot be opened from the main branch and stop.

If there are **no commits ahead of main**, inform the user that there is nothing to open a PR for and stop.

If the `gh` CLI is not authenticated or the remote is not a GitHub repository, inform the user and stop.

### 2. Analyze the changes

From the output of `git log main..HEAD` and `git diff main...HEAD`, extract:

- A concise **title** that summarizes the overall change (≤72 characters, imperative mood, no trailing period)
- A **body** that describes the changes in detail (see format below)

#### PR body format

```
## TL;DR

One sentence explaining the changes in the shortest most concise way possible.

## What changed

<Changes grouped under bold category labels. Only include categories that apply — omit the rest.>

**Added**
- ...

**Changed**
- ...

**Fixed**
- ...

**Removed**
- ...

**Refactored**
- ...

## Notes

<any migration steps, breaking changes, side effects, or reviewer hints that don't fit the categories above — omit this section entirely if there is nothing notable>
```

Rules:

- Use imperative mood throughout ("Add", "Fix", "Remove" — not "Added", "Fixed")
- Be specific: name the files, classes, methods, or endpoints that changed where relevant
- Only include category labels that have at least one item — omit empty categories entirely
- One bullet per logical change, not per commit
- Omit the `## Notes` section entirely if there is nothing notable to call out

### 3. Create or update the pull request

#### If no PR exists for the current branch

```bash
gh pr create \
  --base main \
  --head <current-branch> \
  --title "<title>" \
  --body "$(cat <<'EOF'
<body>
EOF
)"
```

#### If a PR already exists

```bash
gh pr edit <pr-number> \
  --title "<title>" \
  --body "$(cat <<'EOF'
<body>
EOF
)"
```

### 4. Confirm

Report the result to the user:

- Whether the PR was **created** or **updated**
- The PR **title**
- The PR **URL**

---

## Constraints

- Always target `main` as the base branch unless the user **explicitly** specifies a different base
- Never close, merge, or delete the PR
- Never push commits or modify the branch as part of this skill — only manage the PR metadata
- Do not fabricate commit details — derive the title and body strictly from `git log` and `git diff` output
- Do not include co-author trailers or tooling footers in the PR body
