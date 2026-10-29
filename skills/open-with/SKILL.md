---
name: open-with
description: Opens every folder this session has touched — git repository, worktree or plain directory — in VS Code by default, or in Zed, Fresh, File Explorer or any app with a file in apps/, as one workspace where the app supports it, for reviewing, editing or browsing the code.
argument-hint: "[app]"
---

Open the code this session works on in an app — an editor to review the git changes or edit the code, a file manager to browse it. The work often spans several repositories, worktrees, branches or plain directories; open all of them at once, in one workspace where the app supports it.

End state: every root the session touched, open in the app as its file under `apps/` describes, and a report naming every path and branch left out.

Each file in [`apps/`](./apps/) describes one app. Its front matter holds `name`, the value `[app]` takes, and `command`, the executable that must be on the `PATH`. Its `## Open` section holds the commands that open the roots, with `{root}` standing for each one, and every outcome that differs from Step 4's. Add an app by adding a file; this one needs no edit.

## Parameters

- **`[app]`** — the `name` of a file in `apps/`. Defaults to `code`. Refuse any other value, and list the names found.

## Ground rules

1. **Never write.** No workspace file, no worktree, no checkout, no stash. The run changes nothing on disk.
2. **Open only what the session touched.** Never scan sibling directories or a repository's other worktrees for more folders.
3. **Skip a branch that has no checkout.** Never create a worktree or switch a branch to give it one. Report it instead.
4. **Report every skip.** A path or branch left out without a word is indistinguishable from one that was never touched.

## Execution Steps

### Step 1 — Resolve the app

Take `[app]`, or `code` when it is absent, as `{app}`. `Glob` `{path-to-skill}/apps/*.md` and read the front matter of each file. Find the file whose `name` is `{app}`:

- **No match:** stop. Refuse, and list every `name` found.
- **Match:** take it as `{app-file}`. Confirm its `command` is on the `PATH`.

```powershell
Get-Command {command} -ErrorAction SilentlyContinue
```

- **Found:** continue to Step 2.
- **Not found:** stop. Report that `{command}` is not on the `PATH`.

### Step 2 — Collect the touched paths

List every file and directory this session named in a tool call — read, edited, written, searched, or used as a working directory or `-C` target in a shell command.

List every branch this session checked out, created, rebased, or otherwise named in a git command, together with the repository it belongs to.

When the session touched no path, use the session's working directory as the only path.

### Step 3 — Resolve the roots

Take each path as `{directory}` — a directory as it is, a file as its parent directory. Map it to the root of the worktree that holds it:

```powershell
git -C {directory} rev-parse --show-toplevel
```

- **Prints a root:** keep the worktree root.
- **Fails — not a git repository:** keep `{directory}` itself as a plain root.
- **Path no longer exists:** skip it. Record it for Step 5.

Remove duplicate roots. Two worktrees of one repository are two roots — keep both, even when one sits inside the other. Drop a plain root that sits inside another root; the outer root already shows it.

Check each branch from Step 2 against its repository's worktrees:

```powershell
git -C {repository} worktree list --porcelain
```

A branch with no `branch refs/heads/{branch}` line has no checkout. Skip it and record it for Step 5 (ground rule 3). A branch with a checkout outside the roots already kept stays out too — the session never touched that folder (ground rule 2). Record it for Step 5 with its path.

### Step 4 — Open the app

Read the `## Open` section of `{app-file}` and run its commands, substituting every root from Step 3 for `{root}`. Quote every root; worktree paths can hold spaces.

Follow every outcome `{app-file}` lists. It takes precedence over these two:

- **Command exits 0:** continue to Step 5.
- **Command fails:** stop. Report the command and its output.

### Step 5 — Report

Report:

- The app, and every root it opened.
- Every path skipped in Step 3, because it no longer exists.
- Every branch skipped in Step 3, with the reason: no checkout, or checked out at a path the session never touched.
- Every command `{app-file}` printed for the user to run instead of running it.
