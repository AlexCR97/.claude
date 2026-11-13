# Build and test commands

The build and test commands `ticket-implement` runs for each project it modified, chosen by a signal in the project's files. Like `ticket-plan`'s `STACK-HEURISTICS.md`, this is specific to a technology stack — not to a ticket source or a ticket type. Read by Steps 6 and 7.

## Build

Run each build from the project's directory — the one holding its solution file, project file or `package.json`.

| Signal                                  | Build command                          |
| --------------------------------------- | -------------------------------------- |
| `*.sln` or `*.csproj`                   | `dotnet build`                         |
| `package.json` with a `build` script    | `pnpm build`                           |
| `package.json` without a `build` script | `pnpm install` (dependency check only) |
| `*.tf` / `*.bicep`                      | skip — no compile step                 |
| Other                                   | skip and note in the report            |

## Test

A single test runs during a slice's red-green cycle; the full suite runs at the end of the phase. Run both from the test project's directory.

| Signal                                              | Single test                                                  | Full suite         |
| --------------------------------------------------- | ------------------------------------------------------------ | ------------------ |
| a test project's `*.csproj`                         | `dotnet test --filter "FullyQualifiedName~{class}.{method}"` | `dotnet test`      |
| `package.json` with a `test` script                 | `pnpm test -- {test-file} -t "{test-name}"`                  | `pnpm test`        |
| `pyproject.toml` or `pytest.ini`, with `uv.lock`    | `uv run pytest {test-file}::{test-name}`                     | `uv run pytest`    |
| `pyproject.toml` or `pytest.ini`, without `uv.lock` | `python -m pytest {test-file}::{test-name}`                  | `python -m pytest` |
| Other                                               | ask which command runs the tests                             | the same           |

A `test` script that runs in watch mode by default (a bare `vitest`, `jest --watch`) needs its one-shot flag — `--run` for Vitest, `--watchAll=false` for Jest.
