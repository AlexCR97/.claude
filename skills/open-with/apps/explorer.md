---
name: explorer
command: explorer
---

# File Explorer

Opens one Windows File Explorer window per root.

## Open

Convert each root to backslashes first. `git rev-parse` prints `C:/Users/…`, and Explorer does not open a path written with forward slashes. Run one command per root:

```powershell
explorer "{root}"
```

- **Any exit code:** continue. `explorer.exe` exits 1 even when the window opens, so the exit code says nothing about the result.
