---
name: open-with
description: Opens the folder of the task in progress — the git repository, worktree or plain directory the session is working in when invoked — in VS Code, Visual Studio, Zed, Fresh, File Explorer or any app with a file in apps/, for reviewing, editing or browsing the code.
argument-hint: "[app]"
---

Open the code the session is working on in an app — an editor to review the git changes or edit the code, a file manager to browse it. Open the folder of the task in progress when the skill is invoked, not every folder the session has passed through. A task can span several folders — the same change made in two repositories, a branch worked in its own worktree beside the main checkout — and then all of them open, in one workspace where the app supports it.

End state: every root of the task in progress, open in the app as its file under `apps/` describes, and a report naming what was opened and every work root or branch left out.

Each file in [`apps/`](./apps/) describes one app. Its front matter holds `name`, the value `[app]` takes, and `command`, the executable that must be on the `PATH`. Its `## Open` section holds the commands that open the roots, with `{root}` standing for each one, and every outcome that differs from Step 4's. An optional `## Locate` section finds an executable that is not on the `PATH`. Add an app by adding a file; this one needs no edit.

## Parameters

- **`[app]`** — the `name` of a file in `apps/`. Defaults to `code`. Refuse any other value, and list the names found.

## Ground rules

1. **Never write.** No workspace file, no worktree, no checkout, no stash. The run changes nothing on disk.
2. **Open only the task in progress.** A folder the session worked in for an earlier task stays closed. Never scan sibling directories or a repository's other worktrees for more folders.
3. **Paths that only run the session are not work.** Loading a skill, an app file, a `CLAUDE.md`, a rule, a memory, a plugin or a settings file, or writing a memory or a scratchpad file, puts no folder in play — every skill, this one included, is read from `~/.claude`.
4. **Skip a branch that has no checkout.** Never create a worktree or switch a branch to give it one. Report it instead.
5. **Report every work root left out.** A folder left closed without a word is indistinguishable from one that was never worked on.

## Execution Steps

### Step 1 — Resolve the app

Take `[app]`, or `code` when it is absent, as `{app}`. `Glob` `{path-to-skill}/apps/*.md` and read the front matter of each file. Find the file whose `name` is `{app}`:

- **No match:** stop. Refuse, and list every `name` found.
- **Match, with a `## Locate` section:** take it as `{app-file}`. Run that section instead of the check below, and follow its outcomes.
- **Match, without one:** take it as `{app-file}`. Confirm its `command` is on the `PATH`.

```powershell
Get-Command {command} -ErrorAction SilentlyContinue
```

- **Found:** continue to Step 2.
- **Not found:** stop. Report that `{command}` is not on the `PATH`.

### Step 2 — Find the task in progress

Take as the task in progress the user's latest request before this invocation, and the work done for it. When that request did no work on any path — a question, a status check — take the most recent request before it that did.

List the paths that task worked on:

- files it edited or wrote;
- directories its git, build, test or other shell commands ran in or targeted with `-C`;
- files and directories it read or searched to do the work;
- paths the user named as the subject of the work.

Drop every path ground rule 3 covers: `~/.claude/skills/`, `~/.claude/plugins/`, `~/.claude/rules/`, `~/.claude/projects/`, `~/.claude/CLAUDE.md`, `~/.claude/settings*.json`, any `CLAUDE.md` or `AGENTS.md` loaded as instructions, and the scratchpad and temp directories. Keep such a path only when the task's goal is to change it — the user asked to edit a skill, a rule or a `CLAUDE.md`.

List every branch the task checked out, created, rebased, or otherwise named in a git command, together with the repository it belongs to.

Collect, separately, the paths earlier tasks worked on, with the same paths dropped. They are only reported.

When no task in the session worked on a path, use the session's working directory as the only path.

### Step 3 — Resolve the roots

Take each path as `{directory}` — a directory as it is, a file as its parent directory. Map it to the root of the worktree that holds it:

```powershell
git -C {directory} rev-parse --show-toplevel
```

- **Prints a root:** keep the worktree root.
- **Fails — not a git repository:** keep `{directory}` itself as a plain root.
- **Path no longer exists:** skip it. Record it for Step 5.

Remove duplicate roots. Two worktrees of one repository are two roots — keep both, even when one sits inside the other. Drop a plain root that sits inside another root; the outer root already shows it.

When it is unclear whether a root belongs to the task in progress or to an earlier one, ask with `AskUserQuestion` — one option per root, `multiSelect` on — rather than guess. Keep the roots selected, and record the rest for Step 5 as roots of an earlier task. When none is selected, stop and report.

Check each branch from Step 2 against its repository's worktrees:

```powershell
git -C {repository} worktree list --porcelain
```

A branch with no `branch refs/heads/{branch}` line has no checkout. Skip it and record it for Step 5 (ground rule 4). A branch with a checkout outside the roots already kept stays out too — the task never worked on that folder (ground rule 2). Record it for Step 5 with its path.

Resolve the earlier tasks' paths the same way, drop every root already kept, and record the rest for Step 5.

When no root of the task in progress is left, stop and report every path and branch skipped.

### Step 4 — Open the app

Read the `## Open` section of `{app-file}` and run its commands, substituting every root from Step 3 for `{root}`. Quote every root; worktree paths can hold spaces.

Follow every outcome `{app-file}` lists. It takes precedence over these two:

- **Command exits 0:** continue to Step 5.
- **Command fails:** stop. Report the command and its output.

### Step 5 — Report

Report:

- The app, every root it opened, and the task that put them in play, in one line.
- Every root of an earlier task left closed.
- Every path skipped in Step 3, because it no longer exists.
- Every branch skipped in Step 3, with the reason: no checkout, or checked out at a path the task never worked on.
- Every command `{app-file}` printed for the user to run instead of running it.
