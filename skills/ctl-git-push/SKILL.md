---
name: ctl-git-push
description: Push the local git commits to the remote repository.
---

## Execution Steps

Run the following steps **in order**. Do not skip any step.

### 1. Verify there is something to push

Run these in parallel:

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
git remote -v
```

- If no remote exists at all, inform the user and stop — there is nowhere to push.
- If an upstream is set, check how many commits are ahead:
  ```bash
  git log @{u}..HEAD --oneline
  ```
  If the output is empty (nothing ahead of the remote), inform the user there is nothing to push and stop.

### 2. Push

- **If an upstream exists** — push normally:
  ```bash
  git push
  ```

- **If no upstream is set** — set the upstream and push:
  ```bash
  git push --set-upstream origin <current-branch>
  ```

### 3. Confirm

Report the result to the user:
- The hashes and messages of the commits that were pushed
- The remote and branch that was pushed to
- A note if a new upstream was set

---

## Constraints

- Never use `--no-verify` or any flag that bypasses hooks
- Never force-push (`--force`, `-f`) unless the user **explicitly** requests it
- Do not push to `main` or `master`; warn the user if this is attempted
