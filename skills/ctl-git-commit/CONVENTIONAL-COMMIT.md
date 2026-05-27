# Conventional Commit

## Format

```txt
<type>(<optional scope>): <description>

<optional body>
```

## Rules

- **`<type>`** — choose the single most accurate type:

  | Type       | When to use                                             |
  | ---------- | ------------------------------------------------------- |
  | `feat`     | New feature visible to users or consumers of the API/UI |
  | `fix`      | Bug fix visible to users or consumers of the API/UI     |
  | `refactor` | Code restructuring with no behavior change              |
  | `perf`     | Performance improvement                                 |
  | `test`     | Adding or correcting tests                              |
  | `docs`     | Documentation changes only                              |
  | `build`    | Build system, tooling, or dependency changes            |
  | `ops`      | Infrastructure, CI/CD, deployment                       |
  | `style`    | Formatting only (whitespace, semicolons, etc.)          |
  | `chore`    | Miscellaneous tasks (init, config, file moves, etc.)    |

- **`<scope>`** — optional; use a short noun describing the affected area (e.g., `auth`, `api`, `cart`). Omit if the change is truly global or cross-cutting.

- **`<description>`** — mandatory:
  - Imperative mood: "add", "fix", "remove" — **not** "added", "fixing"
  - All lowercase
  - No trailing period
  - Keep it concise (≤72 chars for the header line)

- **Breaking changes** — append `!` before the colon and add a `BREAKING CHANGE:` footer line:

  ```txt
  feat(api)!: remove deprecated v1 endpoints

  BREAKING CHANGE: The /v1/users endpoint has been removed. Migrate to /v2/users.
  ```

- **Body** — include when the *why* or *what* is not obvious from the subject line:
  - Separate from the header with a blank line
  - Wrap at 100 characters per line
  - Explain motivation, not mechanics
  - Omit entirely if the subject line is self-explanatory

## Deciding whether to include a body

Include a body when:

- Multiple distinct changes are bundled in the commit
- The reason for the change is not obvious from the description alone
- Important context would be lost without it

Omit the body when:

- The subject line is fully self-explanatory
- The change is trivial or routine

## Constraints

- Do not infer or fabricate scope — omit it if uncertain
- Do not co-author yourself (Claude or Claude Code)
