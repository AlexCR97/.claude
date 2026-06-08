---
name: ctl-refactor
description: Scan code for refactoring opportunities based on the established guidelines and language-specific conventions. Intended for final polish after development. Presents numbered candidates with before/after code, then offers to apply selected changes.
allowed-tools: Read Grep Glob Bash(git diff:*) Bash(git log:*) Bash(git show:*)
argument-hint: scope
---

# Find Refactoring Candidates

Scan the target code for refactoring opportunities and present them as actionable, numbered candidates. Once the user selects which to apply, implement the changes.

## Supported Scopes

The `$ARGUMENTS` value determines what code to analyze:

- `file <path>` — analyze a single file.
- `dir <path>` — analyze all source files under a directory.
- `changes` — analyze the current git diff (staged + unstaged). Default when no argument is given.
- `branch [<base>]` — analyze changes between the current branch and `<base>` (defaults to `main`).
- `all` — analyze the entire codebase under the current working directory.

If `$ARGUMENTS` is empty, null, or unrecognized, use `changes`.

---

## Step 1 — Detect the Language and Load Conventions

Inspect the files in scope to determine the primary programming language (e.g. by file extensions or project files such as `*.csproj`, `package.json`, `go.mod`, `Cargo.toml`, `requirements.txt`).

Then check whether a language-specific conventions file exists in `.claude/rules/`:

| Language | Convention file                       |
| -------- | ------------------------------------- |
| C#       | `.claude/rules/csharp-conventions.md` |

If a matching file exists, read it and treat every rule it defines as an additional **high-priority** checklist item. Convention-file rules take precedence when they conflict with the checks below.

If no matching file exists, proceed with the remaining steps only.

---

## Step 2 — Load Shared Guidelines

Read `.claude/rules/review-guidelines.md` and apply every item defined there as part of the refactoring checklist.

---

## Step 3 — Apply Refactor-Specific Guidelines

Apply the following additional checks, which are unique to deep quality passes and are not covered in the shared guidelines.

### Encapsulation & Immutability

- State that is exposed for mutation but only needs to be set at construction time.
- Injected dependencies that could be made immutable after construction.
- Types that are not designed for inheritance but are left open to subclassing.
- Implementation details leaked through overly broad visibility modifiers.

### Object Lifecycle & Construction

- Constructors that perform I/O, make network calls, or execute business logic — should be deferred to a factory or init method.
- Objects that can be created in an invalid or partially initialized state.
- Configuration values captured at startup that should be resolved lazily.

### Collections & Null Handling

- Methods that return `null` for a collection type instead of an empty collection.
- Collection-typed fields or return values that allow mutation when read-only access is sufficient.
- Null checks on external or mapped collections that force every caller to guard against `null`.
- String-emptiness checks that pass for whitespace-only values when whitespace should also be rejected.

### Resource Management

- Persistence calls not guarded by a check that the data actually changed.
- Mutation methods that give callers no way to know whether a change occurred, forcing them to persist unconditionally.

## Formatting

- Do file and directory names follow the project's structural conventions?
- Is spacing and indentation consistent with the rest of the codebase?

---

## Candidate Schema

Present each finding as a numbered section using this exact format:

```
## {N}. {Title}

**Code:** `{PascalCaseCode}`
**Category:** {Category}
**Severity:** {Severity}

**Current code** (`{file}:{line range}`):
{code block showing the problematic code}

**Suggested improvement:**
{code block showing the improved version}

**Why:** {in-depth explanation of the benefit — what problem this solves or what property it gains}
```

- **Title**: short, human-readable phrase, e.g. "Mutable Injected Dependency".
- **Code**: unique PascalCase identifier, e.g. `MutableInjectedDependency`.
- **Category**: one of `Encapsulation`, `Object Lifecycle`, `Collections & Null Handling`, `Resource Management`, `Clean Code`, `Naming & Formatting`, `Async & Concurrency`, `Performance`, `Language Conventions`, or `Other`.
- **Severity**: one of `Critical`, `High`, `Medium`, `Low`, `Informational`.

---

## Summary Table

After all candidates, render a markdown table sorted by severity (Critical → Informational), then category, then code:

| #   | Severity | Category | Code | Finding |
| --- | -------- | -------- | ---- | ------- |

Keep the **Finding** column under 150 characters.

---

## Interactive Refactor Step

After the summary table, ask the user exactly this:

> Which candidates would you like me to refactor? Enter their numbers or codes separated by commas, or type **all** to apply every candidate.

Wait for the user's response before making any changes.

Once the user replies:

1. Apply only the selected candidates (or all, if "all" was typed).
2. Edit files in place — do not create new files unless a factory method genuinely warrants a new class file.
3. After applying, output a brief confirmation: which candidates were applied and which files were modified.
4. If a candidate cannot be applied cleanly (e.g. it requires broader context changes), explain why and skip it — do not partially apply.
