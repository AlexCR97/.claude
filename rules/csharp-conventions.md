# C# Coding Conventions

> All runnable code examples can be executed in [C# Online Compiler | .NET Fiddle](https://dotnetfiddle.net/)

---

## Table of Contents

1. [Encapsulation & Access Modifiers](#encapsulation--access-modifiers)
2. [Constructors & Initialization](#constructors--initialization)
3. [Naming Conventions](#naming-conventions)
4. [Collections & Null Handling](#collections--null-handling)
5. [Code Style & Readability](#code-style--readability)
6. [Async & Concurrency](#async--concurrency)
7. [Performance & Resource Management](#performance--resource-management)
8. [Domain-Driven Design](#domain-driven-design)
9. [Design Principles](#design-principles)

---

## Encapsulation & Access Modifiers

### Properties should be encapsulated by default

Favor immutability: only expose a setter when there is a clear reason to allow mutation from outside the class.

By default, a property should have no setter:

```cs
public string Name { get; }
```

If a property can be modified from within the class, use `private set`:

```cs
public string Name { get; private set; }
```

If a property needs to be modified by derived classes, use `protected set`:

```cs
public string Name { get; protected set; }
```

### Class dependencies should be `private readonly`

Dependencies injected into a class should not be reassigned after construction. Mark them `private readonly` to enforce this at compile time.

```cs
// Before
public class OrderService
{
    private IOrderRepository _repository;

    public OrderService(IOrderRepository repository)
    {
        _repository = repository;
    }
}

// After
public class OrderService
{
    private readonly IOrderRepository _repository;

    public OrderService(IOrderRepository repository)
    {
        _repository = repository;
    }
}
```

### Sealed classes cannot be inherited unintentionally

If a class or record is not designed to be subclassed, mark it `sealed`. This communicates intent, prevents accidental inheritance, and enables minor runtime optimizations.

```cs
// A value object that should never be subclassed
public sealed record Money(decimal Amount, string Currency);

// An internal implementation that leaks no extension points
internal sealed class PaymentProcessor : IPaymentProcessor
{
    // ...
}
```

### Internal services should not be accessible outside the assembly

If a service is an implementation detail of a package/project and should not be used by external consumers, mark it `internal`. This enforces encapsulation at the assembly boundary.

```cs
// This service is wired up via DI but not meant to be referenced directly by other projects
internal sealed class EmailNotificationService : INotificationService
{
    // ...
}
```

---

## Constructors & Initialization

### Domain models should always have a full constructor

Avoid empty (parameterless) constructors on domain models. Requiring all properties at construction time ensures the object is always in a valid state.

```cs
// Before: object can exist in an invalid state
public class Product
{
    public string Name { get; set; }
    public decimal Price { get; set; }
}

var p = new Product(); // Name and Price are unset — invalid state

// After: always valid on creation
public class Product
{
    public string Name { get; }
    public decimal Price { get; }

    public Product(string name, decimal price)
    {
        Name = name;
        Price = price;
    }
}
```

### Constructors should initialize, not execute logic

A constructor's responsibility is to wire up dependencies and assign initial values — not to perform business logic, make I/O calls, or throw domain exceptions. Move that logic to a factory method.

```cs
// Before: constructor does too much
public class ReportGenerator
{
    private readonly List<Report> _reports;

    public ReportGenerator(IReportRepository repository)
    {
        _reports = repository.GetAllAsync().Result; // Blocking I/O in constructor — bad
    }
}

// After: initialization is deferred to a factory method
public class ReportGenerator
{
    private readonly IReportRepository _repository;
    private List<Report> _reports = [];

    public ReportGenerator(IReportRepository repository)
    {
        _repository = repository; // Only assign, never execute
    }

    public static async Task<ReportGenerator> CreateAsync(IReportRepository repository)
    {
        var generator = new ReportGenerator(repository);
        generator._reports = await repository.GetAllAsync();
        return generator;
    }
}
```

### Configuration values should be resolved at runtime, not at startup

Reading configuration inside a constructor or at class-definition time means the value is frozen at startup. Resolve configuration values lazily (e.g., via `IOptions<T>` or by reading at the time they are needed) so changes in configuration can take effect without restarting the app.

```cs
// Before: value is captured once at startup and never refreshed
public class FeatureService
{
    private readonly bool _featureEnabled;

    public FeatureService(IConfiguration config)
    {
        _featureEnabled = config.GetValue<bool>("Features:NewCheckout"); // Frozen
    }
}

// After: value is read at the time it is needed
public class FeatureService
{
    private readonly IOptionsMonitor<FeatureOptions> _options;

    public FeatureService(IOptionsMonitor<FeatureOptions> options)
    {
        _options = options;
    }

    public bool IsNewCheckoutEnabled => _options.CurrentValue.NewCheckout;
}
```

---

## Naming Conventions

### Async methods should end with "Async"

Any method whose return type is `Task` or `ValueTask` should have an `Async` suffix to signal to callers that the method must be awaited.

```cs
// Before
public Task<string> GetResult() { }

// After
public Task<string> GetResultAsync() { }
```

### Controller action methods should NOT end with "Async"

ASP.NET Core controller actions are a special case: the framework already knows they are async, and the `Async` suffix adds noise without benefit.

```cs
// Before
public Task<IActionResult> PostSomethingAsync() { }

// After
public Task<IActionResult> PostSomething() { }
```

### Use `As` for casts and `To` for transformations

The prefix of a type-conversion method should communicate whether it is a cheap cast or an allocating transformation.

- `AsOtherType` — casts the object to another type (no new allocation).
- `ToOtherType` — maps/transforms the object into a new instance of another type.

```cs
// Cast: no new object is created
public static TypeB AsTypeB(this TypeA obj) => (TypeB)obj;

// Transformation / Map: a new object is created
public static TypeB ToTypeB(this TypeA obj) => new(obj.Id, obj.Name);
```

### Use `Set` for single-property mutations and `Update` for multi-property mutations

- `SetProperty(value)` — changes exactly one property.
- `Update(...)` — changes several properties at once.

```cs
// Sets a single property
public void SetName(string name)
{
    Name = name;
    LastModifiedDateTime = DateTime.UtcNow;
}

// Updates multiple properties at once
public void Update(string name, string email)
{
    Name = name;
    Email = email;
    LastModifiedDateTime = DateTime.UtcNow;
}
```

### The `Unknown` value of an enum should always be assigned to 0

The default value of an integer in C# is `0`. If an enum field is never explicitly set, it will hold `0`. Naming that value `Unknown` makes uninitialized state explicit and avoids mistakenly treating it as a valid value.

```cs
enum OrderStatus
{
    Unknown = 0,
    Pending,
    Shipped,
    Delivered,
}
```

---

## Collections & Null Handling

### Prefer empty collections over null collections

Returning `null` for a collection forces every caller to perform a null-check before iterating. Returning an empty collection is always safe and removes that burden.

```cs
// Annoying: callers must guard against null
List<int> nums = ReturnNull();

if (nums.Any()) { }                           // NullReferenceException!
if (nums is not null && nums.Any()) { }       // Safe, but verbose

// Better: always return an empty collection instead of null
List<int> nums = ReturnEmpty();

if (nums.Any()) { }                           // Always safe
```

### Null collections should fall back to empty when consuming external data

When mapping or consuming data from external sources (e.g., an API response or database model), always fall back to an empty collection so downstream code does not need to null-check.

```cs
// Before
model.Items
    ?.Select(item => item.ToDto())
    .ToList()

// After
(model.Items ?? [])
    .Select(item => item.ToDto())
    .ToList()
```

### Prefer `IReadOnlyList<T>` for collections that should not be mutated

When exposing a list that callers should only read — not modify — use `IReadOnlyList<T>` as the return or property type. This communicates intent and prevents accidental mutation.

```cs
// Before: caller can Add/Remove items
public List<OrderLine> Lines { get; private set; }

// After: caller can only read
public IReadOnlyList<OrderLine> Lines { get; private set; }
```

### Prefer `IsNullOrWhiteSpace` over `IsNullOrEmpty`

`IsNullOrEmpty` passes for a string that is only whitespace (e.g., `"   "`), which is almost always considered invalid input. Prefer `IsNullOrWhiteSpace` to catch those cases too.

```cs
// Before: passes for "   " (whitespace-only)
if (string.IsNullOrEmpty(input))
    throw new ArgumentException("Input cannot be empty.");

// After: catches null, empty, and whitespace-only
if (string.IsNullOrWhiteSpace(input))
    throw new ArgumentException("Input cannot be empty or whitespace.");
```

### Prefer returning `null` over `default`

When a method returns a reference type and finds no result, return `null` explicitly. Using `default` is less readable and, for value types, silently returns a zeroed value which can be confused for a valid result.

```cs
// Before: ambiguous for value types
public Product? Find(int id) => default;

// After: explicit
public Product? Find(int id) => null;
```

---

## Code Style & Readability

### Mark classes `static` if they are not meant to be instantiated

If a class contains only static members and will never be instantiated, mark it `static`. This prevents accidental instantiation and clearly communicates intent.

```cs
// Before: can be accidentally instantiated
public class MathHelpers
{
    public static int Add(int a, int b) => a + b;
}

// After: cannot be instantiated
public static class MathHelpers
{
    public static int Add(int a, int b) => a + b;
}
```

### Consider using `record` for DTOs and immutable value objects

Records are ideal when:

- The object is a DTO: a Command, Query, Request, Event, Document, etc.
- The properties will never need to be mutated after creation.

```cs
// Command
public record CreateUserCommand(string Username, string Email);

// Query
public record GetUserByIdQuery(Guid UserId);

// Response / DTO
public record UserDto(Guid Id, string Username, string Email);
```

### Prefer method calls over direct property modification

Modifying a property directly from outside the owning class breaks encapsulation. Use a dedicated method instead. This has several benefits:

- **Data protection**: the class owns and manages its own data.
- **Clean state management**: changes happen in one single place.
- **Resource optimization**: the method can return a `bool` to indicate whether the data actually changed, so callers can avoid unnecessary work (e.g., skipping a database call when nothing changed).
- **Traceability**: the IDE can show all call sites for the method.

```cs
// Before: external code mutates the object directly
obj.Name = "some value";

// After: the object manages its own state
obj.SetName("some value");
```

### Refactor deeply nested code using guard clauses

When code has multiple levels of nesting (`if` inside `if` inside `if`), consider extracting it into a method and returning early for each failing condition. This is the *guard clause* pattern and flattens the indentation significantly.

```cs
// Before: pyramid of doom
public void Process(Order? order)
{
    if (order != null)
    {
        if (order.Lines.Count > 0)
        {
            if (order.Customer != null)
            {
                // actual logic
            }
        }
    }
}

// After: guard clauses
public void Process(Order? order)
{
    if (order is null) return;
    if (order.Lines.Count == 0) return;
    if (order.Customer is null) return;

    // actual logic
}
```

### Reduce A-B-A assignments to A-A assignments

When a temporary variable is assigned only to immediately overwrite another variable, the intermediate step is unnecessary.

```cs
// Before: redundant intermediate variable
var currentValue = something.Value;

if (somethingHappened)
{
    var newValue = DoSomething();
    currentValue = newValue;  // A-B-A
}

// After: assign directly
var currentValue = something.Value;

if (somethingHappened)
{
    currentValue = DoSomething();  // A-A
}
```

### Prefer collection initializers over imperative concatenation

When constructing an object whose collection properties need initial values, populate them inline using a collection initializer instead of calling `AddRange` after the fact.

```cs
// Before: two-step initialization
var response = new PaginatedData
{
    Count = other.Count,
    PageIndex = other.PageIndex,
    PageSize = other.PageSize,
};

response.Data.AddRange(other.Data.Select(x => x.ToDto()));

// After: single-step initialization
var response = new PaginatedData
{
    Count = other.Count,
    PageIndex = other.PageIndex,
    PageSize = other.PageSize,
    Data = [..other.Data.Select(x => x.ToDto())],
};
```

### Inline non-trivial one-liners where appropriate

If a helper method returns a simple, self-explanatory expression, prefer writing the expression inline rather than hiding it behind an abstraction.

A **non-trivial** one-liner is short, readable, and makes its intent obvious without a named wrapper.

```cs
// Before: unnecessary wrapper
bool IsValidString(string str) => !string.IsNullOrWhiteSpace(str);

var isValid = IsValidString(input);

// After: readable without the wrapper
var isValid = !string.IsNullOrWhiteSpace(input);
```

### Inline small single-use methods where appropriate

If a private helper method is only a few lines, is straightforward to read, and is called in exactly one place, consider inlining it. The indirection is not buying anything.

```cs
// Before: one-off helper called in a single place
void SaveCache() { /* 2–3 lines */ }

if (!cacheExists)
    SaveCache();

// After: inline the logic directly
if (!cacheExists)
{
    // 2–3 lines of cache-saving logic
}
```

### Prefer computed properties over stateful ones

When a property's value can be derived from other data that is already on the object, compute it on-the-fly instead of storing and manually synchronizing a separate field.

```cs
// Before: manually kept in sync
public string FirstName { get; private set; }
public string LastName { get; private set; }
public string FullName { get; private set; } // Must be updated whenever First/Last changes

public void SetName(string first, string last)
{
    FirstName = first;
    LastName = last;
    FullName = $"{first} {last}"; // Easy to forget
}

// After: always consistent, no manual sync needed
public string FirstName { get; private set; }
public string LastName { get; private set; }
public string FullName => $"{FirstName} {LastName}"; // Derived automatically
```

---

## Async & Concurrency

### Always forward `CancellationToken` to async methods

Any `async` method should accept a `CancellationToken` and pass it to every awaited call. This allows the entire call chain to be cancelled cleanly when the caller requests it (e.g., when an HTTP request is aborted).

```cs
// Before: cancellation is not supported
Task<User> GetUserAsync(Guid id);

// After: cancellation propagates through the entire call chain
Task<User> GetUserAsync(Guid id, CancellationToken cancellationToken = default);
```

### Always check the CancellationToken before expensive operations

In long-running operations, check the token at the start of each iteration or before each expensive step so the work stops promptly when cancelled.

```cs
// General case
cancellationToken.ThrowIfCancellationRequested();

// Inside a gRPC service
context.CancellationToken.ThrowIfCancellationRequested();
```

### Wrap event handlers in `try/catch`

An unhandled exception inside an event handler can crash the entire process. Wrap the body of every event handler in a `try/catch` to isolate failures.

```cs
someService.SomethingHappened += async (sender, args) =>
{
    try
    {
        await HandleSomethingHappenedAsync(args);
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Error handling SomethingHappened event.");
    }
};
```

### Avoid async lambdas inside synchronous `ForEach`

`List<T>.ForEach` is a synchronous method that accepts an `Action<T>`. Passing an `async` lambda makes it return `async void`, which means the caller never awaits the tasks — they fire and are silently ignored. Always use the `foreach` statement when you need to `await` inside the loop.

```cs
// Bad: tasks are fire-and-forget, output order is unpredictable
numbers.ForEach(async num => await PrintWithDelayAsync(num));

// Good: tasks are awaited in sequence
foreach (var num in numbers)
    await PrintWithDelayAsync(num);
```

To demonstrate the problem, consider:

```cs
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

List<int> numbers = [1, 2, 3, 4, 5];

Console.WriteLine("BEGIN foreach statement");
await PrintUsingForeachStatement(numbers);
Console.WriteLine("END foreach statement\n");

Console.WriteLine("BEGIN ForEach method");
await PrintUsingForEachMethod(numbers);
Console.WriteLine("END ForEach method");

async Task PrintUsingForeachStatement(List<int> numbers)
{
    foreach (var num in numbers)
        await PrintWithDelay(num);
}

async Task PrintUsingForEachMethod(List<int> numbers)
{
    numbers.ForEach(async num => await PrintWithDelay(num)); // Does NOT await
}

async Task PrintWithDelay(int number)
{
    await Task.Delay(100);
    Console.Write($"{number} ");
}
```

Output:

```
BEGIN foreach statement
1 2 3 4 5
END foreach statement

BEGIN ForEach method

END ForEach method
```

The `ForEach` version prints nothing because the tasks were never awaited.

---

## Performance & Resource Management

### Only persist to the database if the model actually changed

Before saving an entity, check whether any of its data actually changed. If nothing changed, skip the database call entirely. This reduces unnecessary writes and load on the database.

```cs
var changed = user.SetName(command.NewName);

if (changed)
    await _repository.SaveAsync(user, cancellationToken);
```

### Update/Set methods should return a boolean indicating whether a change occurred

This pairs with the rule above. By returning `true` when data changed and `false` when it did not, callers can make informed decisions — such as skipping a database write — without inspecting the object themselves.

Consider the following example:

```cs
using System;
using System.Text.Json;

var user = User.Create("fizzbuzz", "fizz@buzz.com");

if (user.SetName("fizzbuzz"))
    Console.WriteLine("#1 The user changed");

if (user.SetName("foobar"))
    Console.WriteLine("#2 The user changed");

if (user.Update("foobar", "foo@bar.com"))
    Console.WriteLine("#3 The user changed");

if (user.Update("foobar", "foo@bar.com"))
    Console.WriteLine("#4 The user changed");

Console.WriteLine(user);

class User
{
    private User(string username, string email, DateTime? lastModifiedDateTime)
    {
        Username = username;
        Email = email;
        LastModifiedDateTime = lastModifiedDateTime;
    }

    public string Username { get; private set; }
    public string Email { get; private set; }
    public DateTime? LastModifiedDateTime { get; private set; }

    public static User Create(string username, string email) => new(username, email, null);

    public bool SetName(string username)
    {
        if (Username == username)
            return false;

        Username = username;
        LastModifiedDateTime = DateTime.UtcNow;

        // If supporting domain events, raise them here — only when something actually changed.

        return true;
    }

    public bool Update(string username, string email)
    {
        if ((Username, Email) == (username, email))
            return false;

        Username = username;
        Email = email;
        LastModifiedDateTime = DateTime.UtcNow;

        // If supporting domain events, raise them here — only when something actually changed.

        return true;
    }

    public override string ToString() => JsonSerializer.Serialize(this);
}
```

Output:

```
#2 The user changed
#3 The user changed
{"Username":"foobar","Email":"foo@bar.com","LastModifiedDateTime":"2024-12-18T00:45:57.5731364Z"}
```

`#1` is skipped because the name did not actually change. `#4` is skipped because neither username nor email changed.

### Improve throughput with parallelism

When processing multiple independent items that each require I/O (database queries, HTTP calls, etc.), run them in parallel using `Task.WhenAll` instead of awaiting them sequentially. This can reduce total elapsed time dramatically.

```cs
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;

List<Dto> dtos = Enumerable.Range(0, 100).Select(_ => new Dto()).ToList();

await Benchmark(async () =>
{
    Console.WriteLine("Sequential...");

    foreach (var dto in dtos)
        dto.SequentialProp = await GetIntWithDelay(11);
});

Console.WriteLine();

await Benchmark(async () =>
{
    Console.WriteLine("Parallel...");

    await Task.WhenAll(dtos.Select(async dto =>
    {
        dto.ParallelProp = await GetIntWithDelay(22);
    }));
});

async Task Benchmark(Func<Task> func)
{
    var sw = Stopwatch.StartNew();
    await func();
    sw.Stop();
    Console.WriteLine("Elapsed: " + sw.Elapsed);
}

async Task<int> GetIntWithDelay(int value)
{
    await Task.Delay(10);
    return value;
}

class Dto
{
    public int SequentialProp { get; set; }
    public int ParallelProp { get; set; }
}
```

Output:

```
Sequential...
Elapsed: 00:00:01.0421712

Parallel...
Elapsed: 00:00:00.0126434
```

### Reduce resource pressure with batch processing

Running all tasks in parallel at once (unbounded parallelism) can overwhelm the database, hit rate limits, or exhaust memory. Processing data in smaller batches is slightly slower but avoids these problems:

- Prevents out-of-memory errors when datasets are large.
- Reduces CPU and I/O spikes.
- Allows retrying from the last successful batch on failure.
- Limits simultaneous database connections, reducing lock contention.

```cs
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;

int[] items = Enumerable.Range(0, 1000).ToArray();

await Benchmark(async () =>
{
    Console.WriteLine("Unbounded parallel...");
    await Task.WhenAll(items.Select(_ => SimulateNetworkOperation()));
});

Console.WriteLine();

await Benchmark(async () =>
{
    Console.WriteLine("Batched parallel...");

    const int batchSize = 250;

    for (int offset = 0; offset < items.Length; offset += batchSize)
    {
        int size = Math.Min(batchSize, items.Length - offset);
        await Task.WhenAll(items.Skip(offset).Take(size).Select(_ => SimulateNetworkOperation()));
    }
});

async Task Benchmark(Func<Task> func)
{
    var sw = Stopwatch.StartNew();
    await func();
    sw.Stop();
    Console.WriteLine("Elapsed: " + sw.Elapsed);
}

async Task SimulateNetworkOperation() => await Task.Delay(10);
```

Output:

```
Unbounded parallel...
Elapsed: 00:00:00.0269653

Batched parallel...
Elapsed: 00:00:00.0443675
```

The batched approach is slightly slower but far safer under real-world load.

---

## Domain-Driven Design

### Events should have a unique ID named after the domain model

Every domain event should carry a unique identifier. Name it `{DomainModel}Id` (not just `Id`) so the property is unambiguous when the event is consumed outside the context of the entity that raised it.

```cs
// Before: ambiguous — Id of what?
public record OrderShippedEvent(Guid Id, DateTime ShippedAt);

// After: clear — the ID of the Order that was shipped
public record OrderShippedEvent(Guid OrderId, DateTime ShippedAt);
```

### Mutation methods should reflect whether a change occurred

See [Update/Set methods should return a boolean indicating whether a change occurred](#updateset-methods-should-return-a-boolean-indicating-whether-a-change-occurred).

---

## Design Principles

### YAGNI — You Aren't Gonna Need It

Do not add functionality until it is actually required. Implementing features speculatively wastes time, increases complexity, and often produces code that never gets used (or gets used incorrectly because requirements were not fully known).

> "Always implement things when you actually need them, never when you just foresee that you need them." — Ron Jeffries

- Write code for the requirements you have **now**, not for what you might need **someday**.
- Remove dead code rather than keeping it "just in case".
- Avoid over-engineering abstractions for hypothetical future use-cases.

[What is YAGNI principle (You Aren't Gonna Need It)?](https://www.geeksforgeeks.org/what-is-yagni-principle-you-arent-gonna-need-it/)

### Calling extension methods on `null` objects will not throw by default

In C#, extension methods are syntactic sugar for static method calls. Because the `this` parameter is just a regular parameter, passing `null` is legal and will not throw a `NullReferenceException` on its own — the method simply receives `null` as its first argument.

This can **hide bugs**: if you expect a null reference to surface as an exception but the extension method silently handles (or ignores) it, the failure becomes invisible.

```cs
public static class StringExtensions
{
    public static bool IsEmpty(this string? s) => string.IsNullOrEmpty(s);
}

string? name = null;

// Does NOT throw — extension methods accept null implicitly
bool result = name.IsEmpty(); // true, no exception
```

Always validate `null` explicitly inside extension methods when `null` is not a meaningful input:

```cs
public static string Truncate(this string s, int maxLength)
{
    ArgumentNullException.ThrowIfNull(s);
    return s.Length <= maxLength ? s : s[..maxLength];
}
```

See also: [[Surprising Behavior of Null References in CSharp Extension Methods]]
