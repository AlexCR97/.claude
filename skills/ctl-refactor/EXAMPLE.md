# Examples — ctl-refactor

---

## 1. Refactor current git changes (default)

```bash
/ctl-refactor
```

Scans the current diff (staged + unstaged). Good as a final pass before opening a PR.

---

## 2. Refactor a single file

```bash
/ctl-refactor file src/Orders/OrderService.cs
```

Focuses the scan on one file. Useful when you know which class needs attention.

---

## 3. Refactor an entire directory

```bash
/ctl-refactor dir src/Orders
```

Scans all source files under the given directory. Useful after finishing a feature slice.

---

## 4. Refactor changes on the current branch

```bash
/ctl-refactor branch
```

Compares the current branch against `main` and limits candidates to touched files. To compare against a different base:

```bash
/ctl-refactor branch develop
```

---

## 5. Refactor the entire codebase

```bash
/ctl-refactor all
```

Full scan of the working directory. Best run infrequently as a codebase health check rather than on every PR.

---

## Sample output

Given `src/Orders/OrderService.cs` in a C# project (conventions loaded from `.claude/rules/csharp-conventions.md`):

---

## 1. Mutable Injected Dependency

**Code:** `MutableInjectedDependency`
**Category:** Encapsulation
**Severity:** High

**Current code** (`src/Orders/OrderService.cs:7`):

```csharp
private IOrderRepository _repository;
```

**Suggested improvement:**

```csharp
private readonly IOrderRepository _repository;
```

**Why:** A field injected through the constructor should never be reassigned. Marking it `readonly` enforces this at compile time and signals that the dependency is stable for the lifetime of the object.

---

## 2. Constructor Performs I/O

**Code:** `ConstructorPerformsIO`
**Category:** Object Lifecycle
**Severity:** High

**Current code** (`src/Orders/OrderService.cs:12-16`):

```csharp
public OrderService(IOrderRepository repository)
{
    _repository = repository;
    _cachedOrders = repository.GetAllAsync().Result;
}
```

**Suggested improvement:**

```csharp
public OrderService(IOrderRepository repository)
{
    _repository = repository;
}

public static async Task<OrderService> CreateAsync(
    IOrderRepository repository,
    CancellationToken cancellationToken = default)
{
    var service = new OrderService(repository);
    service._cachedOrders = await repository.GetAllAsync(cancellationToken);
    return service;
}
```

**Why:** Blocking on async work inside a constructor deadlocks in some synchronization contexts and makes the type impossible to instantiate in unit tests without a live database. Moving initialization to a static factory method keeps the constructor simple and makes async + cancellation first-class.

---

## 3. Null Returned for Collection

**Code:** `NullReturnedForCollection`
**Category:** Collections & Null Handling
**Severity:** Medium

**Current code** (`src/Orders/OrderService.cs:31`):

```csharp
public IReadOnlyList<Order> GetPendingOrders()
{
    if (_cachedOrders is null)
        return null;

    return _cachedOrders.Where(o => o.Status == OrderStatus.Pending).ToList();
}
```

**Suggested improvement:**

```csharp
public IReadOnlyList<Order> GetPendingOrders()
{
    if (_cachedOrders is null)
        return [];

    return _cachedOrders.Where(o => o.Status == OrderStatus.Pending).ToList();
}
```

**Why:** Returning `null` for a collection forces every caller to null-check before iterating. An empty list is always safe to iterate and removes that burden entirely.

---

## 4. Missing Async Suffix

**Code:** `MissingAsyncSuffix`
**Category:** Naming & Formatting
**Severity:** Low

**Current code** (`src/Orders/OrderService.cs:45`):

```csharp
public async Task<Order?> FindById(Guid id, CancellationToken cancellationToken = default)
```

**Suggested improvement:**

```csharp
public async Task<Order?> FindByIdAsync(Guid id, CancellationToken cancellationToken = default)
```

**Why:** Any method returning `Task` or `ValueTask` should carry the `Async` suffix so callers know at the call site that the method must be awaited.

---

| #   | Severity | Category                    | Code                      | Finding                                                                                    |
| --- | -------- | --------------------------- | ------------------------- | ------------------------------------------------------------------------------------------ |
| 1   | High     | Encapsulation               | MutableInjectedDependency | `_repository` is not `readonly` — can be reassigned after construction.                    |
| 2   | High     | Object Lifecycle            | ConstructorPerformsIO     | Constructor blocks on `GetAllAsync().Result` — should use a static factory method instead. |
| 3   | Medium   | Collections & Null Handling | NullReturnedForCollection | `GetPendingOrders` returns `null` instead of `[]` when cache is uninitialized.             |
| 4   | Low      | Naming & Formatting         | MissingAsyncSuffix        | `FindById` returns `Task<Order?>` but is missing the `Async` suffix.                       |

---

> Which candidates would you like me to refactor? Enter their numbers or codes separated by commas, or type **all** to apply every candidate.

**User:** 1, 3, 4

Applied candidates: `MutableInjectedDependency`, `NullReturnedForCollection`, `MissingAsyncSuffix`
Modified files: `src/Orders/OrderService.cs`
Skipped: none
