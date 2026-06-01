---
name: ctl-review-code-changes
description: Review the code changes using the established mode and guidelines. Intended for active development and pull request reviews.
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

## Guidelines

### Step 1 — Load Shared Guidelines

Read `.claude/rules/review-guidelines.md` and apply every item defined there as part of this review.

### Step 2 — Apply Review-Specific Guidelines

Apply the following additional checks, which are unique to change-safety reviews and are not covered in the shared guidelines.

#### Functional Requirements

- Are edge cases considered?
- Are the changes backwards compatible?
- Are there any breaking changes?

#### Security

- Is there user input validation?
- Is there any sensitive data being exposed?
- Are there any unwanted packages or libraries being installed?
- Are we allowing remote code execution, SQL injection, or query injection?

#### Resilience

- Is the code resilient under failure? (retry policies, timeouts, circuit breakers)

---

## Finding Schema

Present each finding as a numbered section using this exact format:

```
## {N}. {Title}

**Code:** `{PascalCaseCode}`
**Category:** {Category}
**Severity:** {Severity}

**Description** (`{file}:{line range}`):
{Thorough description of the finding — what is wrong, why it matters, and what to do about it.}
```

- **Title**: short, human-readable phrase, e.g. "Unique Identification Code".
- **Code**: unique PascalCase identifier, e.g. `UniqueIdentificationCode`.
- **Category**: one of `Functional Requirements`, `Security`, `Resilience`, `Clean Code`, `Naming & Formatting`, `Async & Concurrency`, `Performance`, or `Other`.
- **Severity**: one of `Critical`, `High`, `Medium`, `Low`, `Informational`.

---

## Summary Table

At the end of the review, generate a summary table of all findings sorted by severity (Critical → Informational), then category, then code:

| Severity | Category | Code | Finding |
| -------- | -------- | ---- | ------- |

Keep the **Finding** column under 150 characters.
