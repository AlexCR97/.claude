# Examples — ctl-review-dependency-updates

---

## 1. Review unstaged changes (default)

```bash
/ctl-review-dependency-updates
```

Reviews all unstaged dependency changes in the working tree.

---

## 2. Review all current changes (staged + unstaged)

```bash
/ctl-review-dependency-updates current
```

Useful before committing a dependency bump to verify everything looks correct.

---

## 3. Review a branch against main

```bash
/ctl-review-dependency-updates branch
```

Most common usage — reviews the full dependency diff of a PR branch against `main`. To compare against a different base:

```bash
/ctl-review-dependency-updates branch develop
```

---

## 4. Review a specific commit

```bash
/ctl-review-dependency-updates commit
```

The skill will prompt for the commit hash if not provided. You can also pass it directly:

```bash
/ctl-review-dependency-updates commit a3f92c1
```

---

## 5. Review a range of commits

```bash
/ctl-review-dependency-updates commits
```

The skill will prompt for the range. You can also specify it directly:

```bash
/ctl-review-dependency-updates commits a3f92c1..c91fa30
```

---

## Sample output

Given a branch that updates several NuGet packages in a .NET project:

---

## 1. Major Version Bump — Newtonsoft.Json

**Code:** `MajorVersionBump_NewtonsoftJson`
**Category:** Major Version Bump
**Severity:** High

**Description** (`Directory.Packages.props:14`):
`Newtonsoft.Json` was bumped from `12.0.3` to `13.0.3` — a major version change. Major bumps signal breaking changes in the public API. Verify that the consuming code has been updated to accommodate any breaking changes introduced in v13, and that the upgrade was intentional.

---

## 2. Pre-release Version — FluentValidation

**Code:** `PrereleaseVersion_FluentValidation`
**Category:** Pre-release Version
**Severity:** High

**Description** (`Directory.Packages.props:21`):
`FluentValidation` was upgraded to `12.0.0-preview1`, a pre-release build. Pre-release versions are unstable and not recommended for production dependencies. Use the latest stable release instead.

---

## 3. Removed Dependency — AutoMapper

**Code:** `RemovedDependency_AutoMapper`
**Category:** Removed Dependency
**Severity:** Medium

**Description** (`Directory.Packages.props:9`, `src/Api/Api.csproj:18`):
`AutoMapper` has been removed from `Directory.Packages.props` and from `Api.csproj`. A search of the codebase found 6 remaining references to `AutoMapper` types in `src/Api/Mapping/`. If these are dead code, they should be removed. If they are still needed, the package removal is likely unintentional.

---

## 4. Lockfile Not Updated

**Code:** `LockfileNotUpdated`
**Category:** Lockfile Inconsistency
**Severity:** Medium

**Description** (`Directory.Packages.props`):
`Directory.Packages.props` was modified but `packages.lock.json` is not present in the diff. The lockfile must be regenerated (`dotnet restore --force-evaluate`) so the resolved versions match the declared ones. Without this, the actual versions installed in CI may differ from those declared in the manifest.

---

## 5. New Dependency — Polly

**Code:** `NewDependency_Polly`
**Category:** New Dependency
**Severity:** Informational

**Description** (`Directory.Packages.props:31`, `src/Infrastructure/Infrastructure.csproj:12`):
`Polly` (`8.4.2`) was added as a new dependency to the `Infrastructure` project. This is the first time this package appears in the solution. New dependencies expand the project's dependency surface — confirm this addition was intentional and that the version aligns with the rest of the solution's resilience strategy.

---

## 6. Security Fix Added to Non-Entry-Point Module

**Code:** `SecurityFixPlacement_SystemTextJson`
**Category:** Security Fix Placement
**Severity:** Medium

**Description** (`src/App.Core/App.Core.csproj:11`, `src/App.Application/App.Application.csproj:14`):
`System.Text.Json` (`9.0.5`) was added as a direct dependency to `App.Core` and `App.Application`, neither of which contains any source file that directly uses `System.Text.Json` types. This pattern indicates the package is being pinned to resolve a transitive security vulnerability.

Inspecting the project graph, `App.Core` and `App.Application` are not entry points — they are referenced by `App.Api` and `App.ConsoleApp`. The security pin should be placed only in `App.Api.csproj` and `App.ConsoleApp.csproj`, which are the top-level deployable projects. Pinning in intermediate libraries creates redundant version constraints that must be updated independently across every module whenever a new patch is released.

---

## 7. Out-of-Scope Source Code Change

**Code:** `OutOfScopeChange_UserService`
**Category:** Scope Violation
**Severity:** High

**Description** (`src/Application/Users/UserService.cs:88-112`):
`UserService.cs` was modified with changes that appear to be a new feature (a new `GetActiveUsersAsync` method), not a fix for a breaking change introduced by any of the upgraded packages. Non-breaking-change source code modifications should not be bundled into a dependency update PR — they make the change harder to reason about and revert.

---

### Package Changes

| Package                       | From   | To              | Bump        | Status                |
| ----------------------------- | ------ | --------------- | ----------- | --------------------- |
| AutoMapper                    | 12.0.1 | —               | —           | Flagged (Removed)     |
| FluentValidation              | 11.9.0 | 12.0.0-preview1 | Pre-release | Flagged               |
| MediatR                       | 12.2.0 | 12.4.1          | Minor       | OK                    |
| Microsoft.EntityFrameworkCore | 8.0.4  | 8.0.11          | Patch       | OK                    |
| Newtonsoft.Json               | 12.0.3 | 13.0.3          | Major       | Flagged               |
| Polly                         | —      | 8.4.2           | —           | Informational (Added) |
| Serilog                       | 3.1.1  | 3.1.2           | Patch       | OK                    |
| System.Text.Json              | —      | 9.0.5           | —           | Flagged (Added)       |

### Findings

| Severity      | Category               | Code                                | Finding                                                                                           |
| ------------- | ---------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------- |
| High          | Major Version Bump     | MajorVersionBump_NewtonsoftJson     | Newtonsoft.Json bumped from 12.0.3 to 13.0.3. Verify breaking changes are handled.                |
| High          | Pre-release Version    | PrereleaseVersion_FluentValidation  | FluentValidation upgraded to 12.0.0-preview1 — not suitable for production.                       |
| High          | Scope Violation        | OutOfScopeChange_UserService        | New feature added in UserService.cs unrelated to any breaking change in the upgrades.             |
| Medium        | Lockfile Inconsistency | LockfileNotUpdated                  | Directory.Packages.props changed but packages.lock.json was not regenerated.                      |
| Medium        | Removed Dependency     | RemovedDependency_AutoMapper        | AutoMapper removed but 6 references remain in src/Api/Mapping/.                                   |
| Medium        | Security Fix Placement | SecurityFixPlacement_SystemTextJson | System.Text.Json pinned in App.Core and App.Application — should only be in entry point projects. |
| Informational | New Dependency         | NewDependency_Polly                 | Polly 8.4.2 added to Infrastructure — confirm this is intentional.                                |
