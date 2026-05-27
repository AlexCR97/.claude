---
name: ctl-review-code-changes
description: Review the code changes using the established mode and guidelines.
disable-model-invocation: true
allowed-tools: Read Grep Bash(git diff:*)
argument-hint: mode
---

The supported review modes are:
- `default`: An alias for the `unstaged` mode.
- `unstaged`: Review the current changes that are unstaged only.
- `current`: Review the current changes that are both unstaged and staged.
- `commit`: Review the changes in a single commit. If the commit hash is not specified, prompt the user for it.
- `commits`: Review the changes in multiple commits. The commits can be specified in two ways, #1 - a list of commits; or #2 - a range of commits (start commit and end commit, inclusive). If the commits are not specified, prompt the user for them.
- `branch`: Review the changes in comparison to another git branch. If the branch is not specified, compare against the main/master branch.
- `other`: Prompt the user what changes need to be reviewed.

If the mode is not specified, null, empty or invalid, use the `default` mode.

Review the code changes in $ARGUMENTS mode using these guidelines sorted by importance:

1. Functional Requirements
  1. Are edge cases considered?
  2. Are the changes backwards compatible?
  3. Are there any breaking changes?
2. Security
  1. Is there user input validation?
  2. Is there any sensitive data being exposed?
  3. Are there any unwanted packages/libraries being installed?
  4. Are we allowing remote code execution, SQL injection or C# Linq injection?
3. Performance & Scalability
  1. Does the code degrade the performance?
  2. Are there any unnecessary loops, database calls, network requests, etc.?
  3. Is the code performant with large data sets?
  4. Is the code resilient? (retry policies, timeouts, circuit breaker, etc.)
  5. Can the code be optimized using parallelization, batching or streaming?
  6. Can the code be optimized with in-memory or distributed caching?
4. Clean Code
  1. Is the code readable and easy to follow for newcomers into the codebase?
  2. Does the code need to be documented with additional context?
  3. Can the code be reduced with reusable methods?
  4. Can the code be improved using common best practices? DRY, YAGNI, SOLID, etc.
  5. Is there any unnecessary or dead code?
5. Styling & Formatting
  1. Does the code follow naming conventions?
  2. Does the code follow styling conventions? (spacing, indentation, file/directory structure, etc.)

Explain each finding one by one. Each finding should have:
- **Title**: A user-friendly title describing the finding in a few words.
- **Code**: A unique code that identifies this finding in PascalCase format, e.g. `UniqueIdentificationCode`.
- **Category**: One of `Functional Requirements`, `Security`, `Performance & Scalability`, `Clean Code`, `Styling & Formatting`, or `Other`.
- **Severity**: One of `Critical`, `High`, `Medium`, `Low`, `Informational`
- **Description**: Thorough description of the finding.

At the end of the review generate a summary table showcasing each finding, sorted by severity, then category and finally code. The table should have the columns:
- **Severity**
- **Category**
- **Code**
- **Finding**: A brief description with a max length of 150 characters.
