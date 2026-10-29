---
name: fresh
command: fresh
---

# Fresh

Opens one Windows Terminal window named `open-with`, with one tab per root and Fresh running in each, its file explorer showing the root.

Fresh is a terminal editor and works in one directory at a time, so it cannot run inside the session's shell. It needs a terminal of its own.

## Open

Confirm `wt` is on the `PATH`:

```powershell
Get-Command wt -ErrorAction SilentlyContinue
```

- **Found:** run one command per root.

  ```powershell
  wt -w open-with new-tab -d "{root}" fresh .
  ```

- **Not found:** open nothing. Print one line per root for the user to run in their own terminal, and report them.

  ```powershell
  cd "{root}"; fresh .
  ```
