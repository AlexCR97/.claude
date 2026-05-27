---
name: ctl-git-commit
description: Stage all current git changes and commit with a conventional commit message.
---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Gather context

Run these commands in parallel to understand the current state:

- `git status` — identify all modified, staged, and untracked files
- `git diff` — see unstaged changes
- `git diff --cached` — see already-staged changes
- `git log --oneline -10` — understand the recent commit history and message style
- `git branch --show-current` — get the current branch name

If there are **no changes** (working tree clean and nothing staged), inform the user and stop.

### 2. Check for sensitive files

Before staging anything, scan the list of changed files for patterns that typically indicate secrets:

`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials.*`, `secrets.*`, `*secret*`, `*password*`

If any match is found, warn the user, list the files, and ask whether to exclude them before continuing. Do not stage or commit those files without explicit approval.

### 3. Stage all changes

Stage all changes, excluding any sensitive files identified in the previous step:

```bash
git add -A
# If sensitive files must be excluded:
git restore --staged <sensitive-file>
```

### 4. Craft the commit message

Analyze the diff and produce a commit message that follows the **Conventional Commit** specification. See [CONVENTIONAL COMMIT](./CONVENTIONAL-COMMIT.md).

### 5. Commit

Create the commit, passing the message via a heredoc to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
type(scope): description

Optional body explaining the why, not the what.
EOF
)"
```

### 6. Confirm

Report the commit hash and the full commit message to the user.

---

## Constraints

- Never use `--no-verify` or any flag that bypasses hooks
- Never amend a previous commit — always create a new one
- Do not co-author yourself (Claude or Claude Code)
