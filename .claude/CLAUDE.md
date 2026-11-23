## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`AlexCR97/.claude`), managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default label names: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context: a `GLOSSARY-MAP.md` at the repo root; each context's `GLOSSARY.md` and `docs/adr/` live under its directory (`sdlc/`). See `docs/agents/domain.md`.

## Worktrees

Create every worktree under `.claude/worktrees/`, where `claude --worktree` and subagent isolation already put theirs. Name the directory after the branch, with each `/` replaced by `-`:

```bash
git worktree add .claude/worktrees/feat-login -b feat/login
```

`.worktrees/` is for tools other than Claude Code. Never create a worktree anywhere else in the repository. Both directories are gitignored.

A new worktree holds only tracked files. `claude --worktree` copies the gitignored files that `.worktreeinclude` lists; after a manual `git worktree add`, copy them yourself.
