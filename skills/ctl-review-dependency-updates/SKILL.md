---
name: ctl-review-dependency-updates
description: Review dependency update changes for version safety, scope discipline, and ecosystem consistency. Intended for PRs whose primary purpose is bumping package versions.
disable-model-invocation: true
allowed-tools: Read Grep Bash(git diff:*)
argument-hint: mode
---

## Supported Modes

- `default`: An alias for the `unstaged` mode.
- `unstaged`: Review the current changes that are unstaged only.
- `current`: Review the current changes that are both unstaged and staged.
- `commit`: Review the changes in a single commit. If the commit hash is not specified, prompt the user for it.
- `commits`: Review the changes in multiple commits. The commits can be specified in two ways — a list of commits, or a range of commits (start and end, inclusive). If not specified, prompt the user for them.
- `branch`: Review the changes in comparison to another git branch. If not specified, compare against the main/master branch.
- `other`: Prompt the user what changes need to be reviewed.

If the mode is not specified, null, empty, or invalid, use the `default` mode.

---

## Step 1 — Detect the Package Ecosystem

Identify the package manager(s) in use by looking for manifest and lockfile pairs in the diff:

| Ecosystem      | Manifest                                          | Lockfile                                      |
| -------------- | ------------------------------------------------- | --------------------------------------------- |
| Node.js (npm)  | `package.json`                                    | `package-lock.json`                           |
| Node.js (pnpm) | `package.json`                                    | `pnpm-lock.yaml`                              |
| .NET (NuGet)   | `*.csproj`, `*.props`, `Directory.Packages.props` | `packages.lock.json`                          |
| Python         | `requirements.txt`, `pyproject.toml`              | `requirements.lock`, `poetry.lock`, `uv.lock` |

If multiple ecosystems are touched in a single changeset, note it as a structural concern.

---

## Step 2 — Build Package Changes Overview

Before applying any guidelines, construct a table of every package that changed:

| Package | From | To  | Bump | Type |
| ------- | ---- | --- | ---- | ---- |

- **Bump**: `Patch`, `Minor`, `Major`, `Pre-release`, `Downgrade`, or `Non-semver`.
- **Type**: `Updated`, `Added`, or `Removed`.

Use this table as the basis for all subsequent checks.

---

## Step 3 — Apply Guidelines

### Scope

- Every non-package file change must be directly traceable to resolving a breaking change introduced by one of the upgrades in this changeset. Flag any source code change that cannot be explained by a breaking change as out-of-scope.
- If multiple package ecosystems are updated in a single changeset, flag it as a structural concern — mixed-ecosystem PRs are harder to reason about and revert selectively.
- **Dockerfile OS-level package updates** (`apt-get upgrade`, `apk upgrade`, `yum update`, `dnf upgrade`, installation of security-related system packages such as `ca-certificates`, `curl`, or `openssl`, etc.) are an exception to the scope rule. These changes address OS-level CVEs and share the same security intent as package dependency fixes, so they are permitted in a dependency update PR. Flag them at **Informational** severity — not as Scope Violations — and note that keeping OS-level and dependency fixes in separate PRs improves rollback granularity, but bundling them is acceptable when the shared intent is security hardening.

### Version Safety

Assume semver (`major.minor.patch`) unless the versioning scheme is clearly different.

- **Patch** (`x.y.Z`) — bug fixes and security fixes. Safe by default; no flag needed.
- **Minor** (`x.Y.z`) — backward-compatible new features. Safe by default; no flag needed.
- **Major** (`X.y.z`) — breaking changes. **Always flag**, regardless of whether the upgrade appears intentional or the source code was updated to accommodate it.
- **Non-semver** — if a package does not follow semver, reason about the version delta using release notes, tag names, date-based schemes, or commit SHAs. Flag if the safety of the upgrade cannot be determined.
- **Pre-release** (`alpha`, `beta`, `rc`, `preview`, `nightly`, `dev`, etc.) — **always flag**, regardless of semver level. Pre-release builds are unstable by definition.
- **Downgrade** — flag any package whose new version is lower than the previous version, regardless of semver level.

### Newly Added Packages

Flag every package that appears for the first time in the diff (not a version change of an existing entry). Note the package name, version, and which manifest it was added to.

### Removed Packages

Flag every package that is dropped entirely from a manifest. Note whether any source code references to it remain in the codebase.

### Security Fix Placement

When a package is added or pinned specifically to resolve a security vulnerability — rather than because the module directly uses it — it must only appear in **top-level entry point modules**: modules that are not referenced as a dependency by any other module in the same project.

To identify entry point modules, read the project structure beyond the diff:

- **.NET**: inspect all `*.csproj` files in the solution. A project is an entry point if no other project references it via `<ProjectReference>`. Projects with `<OutputType>Exe</OutputType>` or using `Microsoft.NET.Sdk.Web` are always entry points.
- **Node.js (workspaces)**: a package is an entry point if no other `package.json` in the workspace lists it as a `dependency` or `devDependency`.
- **General rule**: deployable artifacts (executables, web apps, CLI tools, Docker image sources) are entry points; shared libraries are not.

**Detecting the pattern**: if a package is newly added to a module as a direct dependency but no source file in that module directly imports or uses the package's public API, it is likely being added for transitive security pinning. Check whether that module is an entry point. If it is not, flag it.

Adding a security fix to a non-entry-point module is a violation — it forces the same fix to be duplicated and maintained independently across every consuming module over time. Pinning only in entry points is sufficient: the resolved version flows down to all transitive dependents automatically.

### Lockfile Consistency

For every manifest file changed, verify that its corresponding lockfile is also present in the diff. Flag if a manifest is modified without a matching lockfile update, or if a lockfile is modified without a corresponding manifest change.

### Version Pinning Strategy

Check that the pinning style of changed entries (`exact`, `^`, `~`, `>=`, etc.) is consistent with other entries in the same manifest. Flag any entry that deviates from the established convention.

### License Changes

If the license of an upgraded or newly added package differs from what was previously declared, flag it. License changes — especially moves toward copyleft or commercial licenses — may introduce obligations the team did not accept when the package was originally adopted.

---

## Finding Schema

Present each finding as a numbered section using this exact format:

```
## {N}. {Title}

**Code:** `{PascalCaseCode}`
**Category:** {Category}
**Severity:** {Severity}

**Description** (`{file}:{line range}`):
{Thorough description — what was found, why it matters, and what to do about it.}
```

- **Title**: short phrase identifying the package and issue, e.g. "Major Version Bump — Newtonsoft.Json".
- **Code**: unique PascalCase identifier, e.g. `MajorVersionBump_NewtonsoftJson`.
- **Category**: one of `Scope Violation`, `Major Version Bump`, `Pre-release Version`, `New Dependency`, `Removed Dependency`, `Security Fix Placement`, `Lockfile Inconsistency`, `Version Pinning`, `Downgrade`, `License Change`, `Non-semver`, or `Other`.
- **Severity**: one of `Critical`, `High`, `Medium`, `Low`, `Informational`.

---

## Summary

After all findings, present two tables.

### Package Changes

Every package that changed, in alphabetical order:

| Package | From | To  | Bump | Status |
| ------- | ---- | --- | ---- | ------ |

- **Status**: `OK`, `Flagged`, or `Informational`.

### Findings

All findings sorted by severity (Critical → Informational), then category, then code:

| Severity | Category | Code | Finding |
| -------- | -------- | ---- | ------- |

Keep the **Finding** column under 150 characters.
