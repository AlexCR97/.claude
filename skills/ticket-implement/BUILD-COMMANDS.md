# Build commands

The build command `ticket-implement` runs for each project it modified, chosen by a signal in the project's files. Like `ticket-plan`'s `STACK-HEURISTICS.md`, this is specific to a technology stack — not to a ticket source or a ticket type. Read by Step 7.

| Signal                                  | Build command                          |
| --------------------------------------- | -------------------------------------- |
| `*.sln` or `*.csproj`                   | `dotnet build`                         |
| `package.json` with a `build` script    | `pnpm build`                           |
| `package.json` without a `build` script | `pnpm install` (dependency check only) |
| `*.tf` / `*.bicep`                      | skip — no compile step                 |
| Other                                   | skip and note in the report            |
