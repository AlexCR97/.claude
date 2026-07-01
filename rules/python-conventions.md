# Python Coding Conventions

> All runnable code examples target Python 3.11+ unless noted otherwise.

---

## Table of Contents

1. [Code Style & Formatting](#code-style--formatting)
2. [Naming Conventions](#naming-conventions)
3. [Type Hints](#type-hints)
4. [Functions & Readability](#functions--readability)
5. [Data Structures & Collections](#data-structures--collections)
6. [Error Handling](#error-handling)
7. [Context Managers & Resource Management](#context-managers--resource-management)
8. [Async & Concurrency](#async--concurrency)
9. [Performance](#performance)
10. [Documentation & Comments](#documentation--comments)
11. [Imports & Project Structure](#imports--project-structure)
12. [Testing](#testing)
13. [Design Principles](#design-principles)

---

## Code Style & Formatting

### Follow PEP 8, enforced by a formatter

Don't hand-format code to match PEP 8 — let a tool do it (`black`, `ruff format`, or `autopep8`). Consistency across a codebase matters more than any individual's preference, and a formatter removes the debate entirely.

```python
# Before: inconsistent spacing, manual line breaks
def total(items,tax_rate = 0.0):
    return sum(i.price for i in items)*(1+tax_rate)

# After: formatter-enforced style
def total(items, tax_rate=0.0):
    return sum(i.price for i in items) * (1 + tax_rate)
```

#### Prefer `uvx ruff` when it's available

When `uvx` and `ruff` are available, lint-fix and format Python code with Ruff via `uvx` — no separate install step needed. First confirm both are available:

```bash
uvx -V        # verify uvx (from uv) is installed
uvx ruff -V   # verify ruff can be resolved and run through uvx
```

If both commands succeed, run the linter (with autofix) first, then the formatter:

```bash
uvx ruff check --fix   # apply lint rules and autofix what it safely can
uvx ruff format        # apply the formatter
```

Run `check --fix` before `format` so that any import sorting or rule fixes are applied before the formatter does its final pass. If either availability check fails, fall back to whatever formatter/linter the project already configures (`black`, `ruff` installed locally, `autopep8`, etc.).

### Prefer f-strings over `%` formatting or `.format()`

f-strings are more readable and faster than the alternatives. Reserve `.format()` for cases where the template is built dynamically (e.g., loaded from a config file).

```python
# Before
message = "User %s has %d items" % (name, count)
message = "User {} has {} items".format(name, count)

# After
message = f"User {name} has {count} items"
```

### Limit line length and let the linter catch violations

Keep lines under ~88-100 characters (the `black` default is 88). Long lines are a readability problem; a linter catching them in CI is cheaper than catching them in review.

---

## Naming Conventions

### Use the standard casing per identifier kind

| Kind | Convention | Example |
|---|---|---|
| Variables, functions, methods | `snake_case` | `total_price`, `get_user()` |
| Classes, exceptions | `PascalCase` | `OrderService`, `InvalidStateError` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |
| Modules, packages | short `lowercase` (no underscores if avoidable) | `orders.py`, `payments/` |
| "Private" attributes/methods | leading underscore | `self._cache` |
| Name-mangled attributes | leading double underscore | `self.__internal_id` |

### A single leading underscore signals "internal", not "enforced private"

Python has no true access modifiers. A single underscore (`_value`) is a convention meaning "implementation detail, don't touch from outside" — it's a signal to callers and tools (like `from module import *`), not a compiler-enforced restriction. Don't reach for double-underscore name mangling (`__value`) to "protect" an attribute; reserve it for the narrow case of avoiding name clashes in subclassing.

### Avoid single-letter and ambiguous names outside tight scopes

Single-letter names are fine for short-lived loop counters or comprehension variables (`i`, `x`), but anything with broader scope or business meaning should be descriptive.

```python
# Before
def calc(o, r):
    return o * (1 + r)

# After
def apply_interest(principal, rate):
    return principal * (1 + rate)
```

### Boolean names should read as a predicate

Prefix booleans with `is_`, `has_`, `can_`, or `should_` so the name reads naturally in an `if` statement.

```python
# Before
active = True
deleted = False

# After
is_active = True
has_been_deleted = False
```

---

## Type Hints

### Annotate public function signatures

Type hints document intent, let static checkers (`mypy`, `pyright`) catch mismatches before runtime, and improve editor autocomplete. At minimum, annotate the parameters and return type of public functions and methods.

```python
# Before
def get_user(user_id):
    ...

# After
def get_user(user_id: int) -> User | None:
    ...
```

### Prefer `X | None` over `Optional[X]`

Since Python 3.10, the `|` union syntax is the idiomatic way to express optional or union types — it requires no import and reads more naturally.

```python
# Before
from typing import Optional

def find(name: str) -> Optional[User]:
    ...

# After
def find(name: str) -> User | None:
    ...
```

### Use `dataclasses` or `TypedDict` instead of untyped dicts for structured data

A bare `dict` passed around as a quasi-object hides its shape from readers and tools. If the data has a fixed, known structure, model it.

```python
# Before: shape is implicit, easy to typo a key
def make_user(name, email):
    return {"name": name, "email": email, "active": True}

# After: shape is explicit and checked
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str
    active: bool = True
```

### Don't let type hints replace runtime validation at boundaries

Type hints are not enforced at runtime (except by optional tools). At system boundaries — parsing user input, deserializing API payloads — validate explicitly (e.g., with `pydantic` or manual checks) rather than trusting the annotation alone.

### Type-check with `uvx ty` when it's available

When `uvx` and `ty` are available, type-check Python code with `ty` via `uvx` — no separate install step needed. First confirm both are available:

```bash
uvx -V         # verify uvx (from uv) is installed
uvx ty --version   # verify ty can be resolved and run through uvx
```

If both commands succeed, run the type checker and fix the issues it reports:

```bash
uvx ty check   # run the type checker across the project
```

Resolve every reported error before considering the change complete — fix the underlying type mismatch rather than silencing it with a blanket ignore. If either availability check fails, fall back to whatever type checker the project already configures (`mypy`, `pyright`, etc.).

---

## Functions & Readability

### Never use a mutable default argument

Default argument values are evaluated **once**, at function-definition time, not per call. A mutable default (list, dict, set) is shared and accumulates state across calls — a classic Python footgun.

```python
# Before: the list persists across calls
def add_item(item, items=[]):
    items.append(item)
    return items

add_item("a")  # ["a"]
add_item("b")  # ["a", "b"]  <- unexpected!

# After: default is None, a fresh list is created per call
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### Favor guard clauses over deep nesting

Return early for invalid or trivial cases instead of nesting the main logic inside multiple `if` blocks.

```python
# Before: pyramid of doom
def process(order):
    if order is not None:
        if order.lines:
            if order.customer is not None:
                ...  # actual logic

# After: guard clauses
def process(order):
    if order is None:
        return
    if not order.lines:
        return
    if order.customer is None:
        return

    ...  # actual logic
```

### A function should do one thing

If a function name needs "and" to describe what it does (`validate_and_save`), it's a sign it should be split. Smaller, single-purpose functions are easier to test and reuse.

### Prefer keyword arguments for functions with several parameters

Once a function has more than two or three parameters — especially same-typed ones — require callers to pass them by keyword to avoid positional mix-ups.

```python
# Before: easy to swap width/height by accident
def resize(image, 800, 600, True):
    ...

# After: force keyword arguments after the first
def resize(image, *, width: int, height: int, keep_aspect: bool = True):
    ...

resize(image, width=800, height=600, keep_aspect=True)
```

---

## Data Structures & Collections

### Prefer comprehensions over manual accumulation loops

Comprehensions are more concise and, for simple transformations/filters, more idiomatic and often faster than building a list with `.append()` in a loop.

```python
# Before
squares = []
for n in numbers:
    if n % 2 == 0:
        squares.append(n * n)

# After
squares = [n * n for n in numbers if n % 2 == 0]
```

Don't take this too far — if the comprehension needs nested loops or complex conditionals that hurt readability, a regular loop (or a generator function) is clearer.

### Prefer generators for large or lazy sequences

When a sequence is only iterated once and doesn't need full materialization, use a generator expression or `yield` instead of building a list in memory.

```python
# Before: builds the entire list in memory
def read_large_file(path):
    return [line.strip() for line in open(path)]

# After: lazy, constant memory
def read_large_file(path):
    for line in open(path):
        yield line.strip()
```

### Use `collections` and `itertools` instead of reimplementing them

`collections.Counter`, `collections.defaultdict`, `itertools.groupby`, `itertools.chain`, etc. are battle-tested and communicate intent better than hand-rolled equivalents.

```python
# Before
counts = {}
for word in words:
    counts[word] = counts.get(word, 0) + 1

# After
from collections import Counter

counts = Counter(words)
```

### Unpack tuples instead of indexing

Indexing into a tuple (`result[0]`, `result[1]`) hides what each element represents. Unpack with descriptive names instead.

```python
# Before
result = divmod(17, 5)
quotient = result[0]
remainder = result[1]

# After
quotient, remainder = divmod(17, 5)
```

---

## Error Handling

### Catch specific exceptions, never bare `except:`

A bare `except:` (or `except Exception:` without re-raising) silently swallows bugs — including `KeyboardInterrupt` and `SystemExit` in the bare case. Catch only the exception types you can meaningfully handle.

```python
# Before: hides every possible failure, including typos and bugs
try:
    process(data)
except:
    pass

# After: handles the one failure mode that's expected
try:
    process(data)
except ValidationError as exc:
    logger.warning("Invalid data: %s", exc)
```

### Prefer EAFP over LBYL when checking is itself the expensive or racy part

"Easier to Ask Forgiveness than Permission" (try/except) is idiomatic Python, especially when the check-then-act sequence could race (e.g., file existence, dict keys) or when the check duplicates work the operation already does.

```python
# Before (LBYL): a TOCTOU race — file could vanish between the check and the open
if os.path.exists(path):
    with open(path) as f:
        data = f.read()

# After (EAFP)
try:
    with open(path) as f:
        data = f.read()
except FileNotFoundError:
    data = None
```

### Raise custom exceptions for domain-specific failures

Don't raise bare `Exception` or reuse built-ins (`ValueError`, `RuntimeError`) for every domain failure. A custom exception hierarchy lets callers catch precisely what they expect.

```python
# Before
raise ValueError("insufficient funds")

# After
class InsufficientFundsError(Exception):
    def __init__(self, balance: float, requested: float):
        self.balance = balance
        self.requested = requested
        super().__init__(f"balance {balance} cannot cover {requested}")

raise InsufficientFundsError(balance=10.0, requested=50.0)
```

### Use `raise ... from ...` when re-raising inside an `except` block

Chaining preserves the original traceback context, making debugging far easier than letting Python implicitly chain it (or worse, losing it by raising a brand-new exception).

```python
try:
    parse(raw_input)
except json.JSONDecodeError as exc:
    raise ConfigError("invalid configuration file") from exc
```

---

## Context Managers & Resource Management

### Always use `with` for resources that need cleanup

Files, locks, network connections, and database sessions should be acquired via `with` so cleanup happens even if an exception is raised — never rely on manual `.close()` calls.

```python
# Before: leaks the file handle if read() raises
f = open(path)
data = f.read()
f.close()

# After: guaranteed to close
with open(path) as f:
    data = f.read()
```

### Write a context manager when a resource pattern repeats

If the same acquire/release pattern shows up in multiple places, wrap it with `contextlib.contextmanager` (or a class implementing `__enter__`/`__exit__`) instead of duplicating try/finally blocks.

```python
from contextlib import contextmanager

@contextmanager
def timed_operation(name: str):
    start = time.monotonic()
    try:
        yield
    finally:
        logger.info("%s took %.2fs", name, time.monotonic() - start)

with timed_operation("import"):
    run_import()
```

---

## Async & Concurrency

### Never call blocking I/O inside an `async def` function

A blocking call (`requests.get`, `time.sleep`, synchronous file I/O) inside a coroutine stalls the entire event loop, defeating the purpose of async. Use the async-native equivalent (`httpx.AsyncClient`, `asyncio.sleep`, `aiofiles`) or offload it with `asyncio.to_thread`.

```python
# Before: blocks the event loop
async def fetch_page(url):
    return requests.get(url).text

# After: non-blocking
async def fetch_page(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

### Run independent awaitables concurrently with `asyncio.gather`

Awaiting independent coroutines one at a time sequentializes work that could run concurrently.

```python
# Before: sequential, slower
results = []
for url in urls:
    results.append(await fetch_page(url))

# After: concurrent
results = await asyncio.gather(*(fetch_page(url) for url in urls))
```

### Bound concurrency with a semaphore when fanning out to many tasks

Unbounded `asyncio.gather` over a large input can exhaust connections or trigger rate limits. Use `asyncio.Semaphore` to cap how many run at once.

```python
sem = asyncio.Semaphore(10)

async def fetch_bounded(url):
    async with sem:
        return await fetch_page(url)

results = await asyncio.gather(*(fetch_bounded(u) for u in urls))
```

---

## Performance

### Profile before optimizing

Don't guess at bottlenecks. Use `cProfile`, `timeit`, or `py-spy` to find the actual hot path before rewriting code for performance — premature optimization usually trades readability for a speedup that doesn't matter.

### Cache expensive, pure computations

Use `functools.lru_cache` (or `functools.cache` in 3.9+) for deterministic, side-effect-free functions that are called repeatedly with the same arguments.

```python
from functools import cache

@cache
def fibonacci(n: int) -> int:
    return n if n < 2 else fibonacci(n - 1) + fibonacci(n - 2)
```

### Use built-in/stdlib operations over manual Python loops

CPython's built-ins (`sum`, `max`, `sorted`, `any`, `all`) and stdlib functions are implemented in C and are almost always faster than the equivalent hand-written loop.

```python
# Before
total = 0
for n in numbers:
    total += n

# After
total = sum(numbers)
```

### Batch I/O instead of issuing it per item

Looping over a collection and issuing one database query or HTTP call per item (the "N+1" problem) doesn't scale. Batch reads/writes or use bulk APIs where available.

---

## Documentation & Comments

### Write docstrings for public modules, classes, and functions

A docstring documents the *contract* (what it does, parameters, return value, exceptions raised) for anyone calling the code without reading its body. Follow PEP 257 conventions — triple double-quotes, a one-line summary, blank line, then details if needed.

```python
def apply_discount(price: float, percent: float) -> float:
    """Apply a percentage discount to a price.

    Args:
        price: The original price, must be non-negative.
        percent: Discount percentage in the range [0, 100].

    Returns:
        The discounted price.

    Raises:
        ValueError: If percent is outside [0, 100].
    """
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return price * (1 - percent / 100)
```

### Default to no comments; only explain the non-obvious

Well-named identifiers and docstrings cover *what* the code does. Reserve inline comments for the *why*: a hidden constraint, a subtle invariant, a workaround for a specific bug.

```python
# Bad: restates the code
# increment retries by 1
retries += 1

# Good: explains a non-obvious constraint
# Stripe's webhook endpoint times out at 3 retries; beyond that
# we fall back to manual reconciliation instead of retrying forever.
if retries >= 3:
    schedule_manual_review(event)
```

---

## Imports & Project Structure

### Avoid wildcard imports

`from module import *` pollutes the namespace, hides where names come from, and breaks static analysis. Import only what's needed, or import the module and qualify access.

```python
# Before
from os.path import *

# After
from os.path import join, exists
```

### Use absolute imports within a package

Absolute imports (`from myapp.services.orders import OrderService`) are clearer than relative ones (`from ..services.orders import OrderService`) about where a symbol lives, and they survive file moves more predictably.

### Keep import order consistent: stdlib, third-party, local

Group imports into three blocks — standard library, third-party packages, local application code — separated by a blank line. Tools like `isort` or `ruff` enforce this automatically.

```python
import json
import os

import httpx
import pydantic

from myapp.models import User
from myapp.services import OrderService
```

### Avoid circular imports by depending on abstractions, not concrete modules

If two modules need to import each other, it's usually a sign that shared logic should be extracted into a third module, or that a dependency should be injected rather than imported directly.

---

## Testing

### Follow Arrange-Act-Assert in test bodies

Structure each test into three clear sections so the intent is obvious at a glance: set up inputs, perform the action, verify the outcome.

```python
def test_apply_discount_reduces_price():
    # Arrange
    price = 100.0

    # Act
    result = apply_discount(price, percent=20)

    # Assert
    assert result == 80.0
```

### Use fixtures instead of duplicating setup code

In `pytest`, extract shared setup into fixtures rather than copy-pasting the same construction logic across test functions.

```python
@pytest.fixture
def order():
    return Order(customer=Customer(name="Jane"), lines=[OrderLine("sku-1", qty=2)])

def test_total_includes_all_lines(order):
    assert order.total() == 2 * order.lines[0].unit_price
```

### Test one behavior per test function

A test named `test_order_processing` that asserts five unrelated things makes failures ambiguous. Prefer many small, descriptively named tests (`test_order_rejects_empty_lines`, `test_order_applies_tax`) over one broad test.

### Parametrize tests that repeat the same logic with different inputs

Use `@pytest.mark.parametrize` instead of copy-pasting near-identical test functions for different inputs/outputs.

```python
@pytest.mark.parametrize(
    ("price", "percent", "expected"),
    [
        (100.0, 0, 100.0),
        (100.0, 50, 50.0),
        (100.0, 100, 0.0),
    ],
)
def test_apply_discount(price, percent, expected):
    assert apply_discount(price, percent) == expected
```

---

## Design Principles

### YAGNI — You Aren't Gonna Need It

Do not add functionality, configuration options, or abstractions until they're actually required. Write code for the requirements you have now.

### The Zen of Python (`import this`)

A handful of its lines act as everyday tie-breakers when a design choice is ambiguous:

- *"Explicit is better than implicit."* — avoid magic; prefer code that states what it does.
- *"Simple is better than complex."* — reach for the simplest construct that solves the problem.
- *"Flat is better than nested."* — favor guard clauses and early returns over deep nesting.
- *"There should be one — and preferably only one — obvious way to do it."* — follow established idioms rather than inventing a personal style.
- *"Readability counts."* — when in doubt, optimize for the next reader.

### Composition over inheritance

Prefer composing small, focused objects (or passing functions/strategies as dependencies) over building deep inheritance hierarchies. Python's duck typing and first-class functions make composition cheap and usually more flexible than subclassing.

### Don't repeat yourself (DRY) — but don't abstract prematurely

Extract duplicated logic into a shared function once a real third occurrence appears. Two similar-looking blocks are often a coincidence, not a pattern; abstracting too early produces the wrong abstraction.

---

## References

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484 — Type Hints](https://peps.python.org/pep-0484/)
- [The Zen of Python — PEP 20](https://peps.python.org/pep-0020/)
- [The Hitchhiker's Guide to Python](https://docs.python-guide.org/)
- [Effective Python — Brett Slatkin](https://effectivepython.com/)
