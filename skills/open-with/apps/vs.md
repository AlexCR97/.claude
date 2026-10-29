---
name: vs
command: devenv
---

# Visual Studio

Opens one Visual Studio window per root, in Open Folder mode. Visual Studio has no multi-root workspace.

## Locate

`devenv.exe` is rarely on the `PATH`. Try the `PATH` first:

```powershell
(Get-Command devenv.exe -ErrorAction SilentlyContinue).Source
```

When that prints nothing, ask the Visual Studio Installer's `vswhere.exe`, which always sits at this path:

```powershell
& "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property productPath
```

- **Prints a path:** take it as `{devenv}`.
- **Prints nothing, or `vswhere.exe` is missing:** stop. Report that Visual Studio is not installed.

## Open

Run one command per root. Start `devenv.exe` through `Start-Process`, never as a bare `devenv`: that resolves to `devenv.com`, the console variant, which holds the shell until Visual Studio closes.

```powershell
Start-Process "{devenv}" -ArgumentList '"{root}"'
```

- **Throws:** stop. Report the command and the error.
- **Returns:** continue.
