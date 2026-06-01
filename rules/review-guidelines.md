# Review Guidelines

Shared checklist applied by both `ctl-review-code-changes` and `ctl-refactor`. Each skill loads this file and applies every item here before applying its own exclusive guidelines.

---

## Clean Code

- Is the code readable and easy to follow for newcomers?
- Does the code contain non-obvious logic that needs a comment explaining _why_ (a hidden constraint, a subtle invariant, a workaround for a specific bug)?
- Is duplicated logic extracted into a reusable abstraction? (DRY)
- Are there speculative features or abstractions added without a current requirement? (YAGNI)
- Are SOLID principles followed — single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion?
- Is there unnecessary or dead code that can be removed?
- Are deeply nested conditionals flattened using guard clauses or early returns?
- Are there trivial single-use private helpers whose body is simple enough to inline?
- Are there stored properties whose value could instead be derived on-the-fly from other data already on the object?

## Async & Concurrency

- Are there async operations that fire work without awaiting it (fire-and-forget inside loops)?
- Are independent I/O-bound operations awaited sequentially when they could run concurrently?
- Do async methods accept and propagate a cancellation signal to their callees?
- Are event handlers or callbacks wrapped to isolate their failures from the surrounding process?

## Performance

- Are there unnecessary loops, repeated computations, or redundant database or network calls?
- Is the code performant with large data sets?
- Can throughput be improved with parallelization, batching, or streaming?
- Can repeated expensive lookups be reduced with in-memory or distributed caching?

## Naming & Formatting

- Do identifiers (types, methods, variables, parameters) follow the project's naming conventions?
- Do method names clearly indicate intent with verbs? e.g. bad -> ReRunEvent, good -> RequestEventReRun
- Do file and directory names follow the project's structural conventions?
- Is spacing and indentation consistent with the rest of the codebase?
