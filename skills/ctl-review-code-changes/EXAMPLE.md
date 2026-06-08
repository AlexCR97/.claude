# Examples — ctl-review-code-changes

---

## 1. Review unstaged changes (default)

```bash
/ctl-review-code-changes
```

Reviews everything not yet staged. Equivalent to `git diff`.

---

## 2. Review all current changes (staged + unstaged)

```bash
/ctl-review-code-changes current
```

Useful before committing to catch anything in the full working-tree diff.

---

## 3. Review a specific commit

```bash
/ctl-review-code-changes commit
```

The skill will prompt for the commit hash if not provided. You can also pass it directly:

```bash
/ctl-review-code-changes commit a3f92c1
```

---

## 4. Review a range of commits

```bash
/ctl-review-code-changes commits
```

The skill will prompt for the range. You can also specify it directly as a list or a range:

```bash
/ctl-review-code-changes commits a3f92c1 b7e14d2 c91fa30
/ctl-review-code-changes commits a3f92c1..c91fa30
```

---

## 5. Review a branch against main

```bash
/ctl-review-code-changes branch
```

Compares the current branch against `main`. To compare against a different base:

```bash
/ctl-review-code-changes branch develop
```

---

## 6. Review something specific

```bash
/ctl-review-code-changes other
```

The skill will ask what to review — useful for reviewing a file snapshot, a generated diff, or any other ad-hoc scope.

---

## 7. Fast mode — bugs only (unstaged)

```bash
/ctl-review-code-changes fast
```

Skips clean code, naming, performance and all of the guideline checks. Focuses exclusively on bugs and broken functionality. Defaults to staged and unstaged changes when no scope is given.

---

## 8. Fast mode — bugs only (specific scope)

```bash
/ctl-review-code-changes fast branch
/ctl-review-code-changes fast commit a3f92c1
/ctl-review-code-changes fast current
```

`fast` can be combined with any change scope mode. Useful when you want deadline-speed feedback on a branch or commit without the full checklist.

---

## Sample output

Given a changeset that adds a new `OrderService` class:

---

## 1. Missing Input Validation

**Code:** `MissingInputValidation`
**Category:** Security
**Severity:** High

**Description** (`src/Orders/OrderService.cs:14-18`):
`CreateOrder` accepts a `customerId` parameter but never validates that it is a non-empty GUID before passing it to the repository. A malformed or empty ID will reach the database and either cause a silent failure or an unhelpful exception at the persistence layer. Validate the parameter at the boundary and return a domain error immediately.

---

## 2. Breaking Change — Removed Constructor Overload

**Code:** `RemovedConstructorOverload`
**Category:** Functional Requirements
**Severity:** Critical

**Description** (`src/Orders/OrderService.cs:8`):
The parameterless constructor `OrderService()` has been removed. At least two existing callers in `tests/` and one in `Program.cs` depend on it. This is a breaking change that will cause compilation failures in consumers that have not been updated.

---

## 3. Sequential Awaits on Independent Queries

**Code:** `SequentialAwaitsOnIndependentQueries`
**Category:** Async & Concurrency
**Severity:** Medium

**Description** (`src/Orders/OrderService.cs:42-45`):
`GetOrderSummaryAsync` awaits `_customerRepository.GetAsync` and `_productRepository.GetAsync` sequentially, but the two queries are independent. Running them concurrently with `Task.WhenAll` would halve the latency for this operation under normal load.

---

| Severity | Category                | Code                                 | Finding                                                                                       |
| -------- | ----------------------- | ------------------------------------ | --------------------------------------------------------------------------------------------- |
| Critical | Functional Requirements | RemovedConstructorOverload           | Parameterless constructor removed — breaks existing callers in tests and Program.cs.          |
| High     | Security                | MissingInputValidation               | `customerId` not validated before reaching the repository — malformed IDs pass silently.      |
| Medium   | Async & Concurrency     | SequentialAwaitsOnIndependentQueries | Customer and product queries awaited sequentially — could run concurrently with Task.WhenAll. |

---

## Sample output — fast mode

Given the same changeset with `fast` mode active, only production-breaking issues surface:

---

### 1. Missing Input Validation (fast)

**Code:** `MissingInputValidation`
**Category:** Security
**Severity:** High

**Description** (`src/Orders/OrderService.cs:14-18`):
`CreateOrder` accepts a `customerId` parameter but never validates that it is a non-empty GUID before passing it to the repository. A malformed or empty ID will reach the database and either cause a silent failure or an unhelpful exception at the persistence layer. Validate the parameter at the boundary and return a domain error immediately.

---

### 2. Breaking Change — Removed Constructor Overload (fast)

**Code:** `RemovedConstructorOverload`
**Category:** Functional Requirements
**Severity:** Critical

**Description** (`src/Orders/OrderService.cs:8`):
The parameterless constructor `OrderService()` has been removed. At least two existing callers in `tests/` and one in `Program.cs` depend on it. This is a breaking change that will cause compilation failures in consumers that have not been updated.

---

| Severity | Category                | Code                       | Finding                                                                                  |
| -------- | ----------------------- | -------------------------- | ---------------------------------------------------------------------------------------- |
| Critical | Functional Requirements | RemovedConstructorOverload | Parameterless constructor removed — breaks existing callers in tests and Program.cs.     |
| High     | Security                | MissingInputValidation     | `customerId` not validated before reaching the repository — malformed IDs pass silently. |

The `SequentialAwaitsOnIndependentQueries` finding from the full review does not appear here — `fast` mode skips `Async & Concurrency` checks.
