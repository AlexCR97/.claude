# Stack heuristics

The project signals and estimate baselines `ticket-plan` uses. They are specific to a technology stack — not to a ticket source or a ticket type — so they live here rather than in `SKILL.md`. Generalizing them into conventions per language, the way `ticket-providers/` and `ticket-types/` hold the other two axes, is out of scope.

## Project signals

Read by Steps 4 and 5, in order of priority.

| Signal                                                                     | What it implies                       |
| -------------------------------------------------------------------------- | ------------------------------------- |
| `*.sln`, `*.csproj`                                                        | .NET backend service or library       |
| `package.json` (with `"scripts"."start"` or framework deps)                | Node/JS/TS service or frontend app    |
| `Dockerfile`, `docker-compose.yml`                                         | Containerized service boundary        |
| `*.bicep`, `*.tf`, `*.tfvars`, `azure-pipelines.yml`, `.github/workflows/` | Infrastructure / DevOps / CI-CD       |
| `**/appsettings*.json`, `**/program.cs`                                    | ASP.NET Web API or background service |
| `angular.json`, `next.config.*`, `vite.config.*`, `nuxt.config.*`          | Frontend SPA framework                |
| `*migrations*`, `*schema*`, `*seed*` (directories or files)                | Database layer                        |
| `*.http`, `openapi.json`, `swagger.json`                                   | API contract definitions              |

## Estimate baselines

Read by Step 9.

| Signal                                              | Baseline |
| --------------------------------------------------- | -------- |
| DB migration (add column / new table)               | 0.5 hr   |
| New API endpoint (controller + service + tests)     | 1.5 hrs  |
| Modify existing API endpoint                        | 0.5–1 hr |
| New frontend component or page                      | 1–2 hrs  |
| Modify existing frontend component                  | 0.5–1 hr |
| Integration / E2E test suite                        | 1–2 hrs  |
| CI pipeline change                                  | 0.5 hr   |
| IaC / infra change                                  | 1 hr     |
| Cross-cutting concern (auth, logging, feature flag) | 1–2 hrs  |

Adjust up for:

- New patterns not already established in the project (+50%)
- Changes that touch more than 5 files (+25% per additional 5 files)

Adjust down for:

- Highly repetitive changes following an obvious existing pattern (−25%)
