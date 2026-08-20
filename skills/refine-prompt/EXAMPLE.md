# Examples — refine-prompt

---

## 1. Refine a prompt passed inline

```bash
/refine-prompt add caching to the orders API so it's faster
```

---

## 2. Refine a prompt stored in a file

```bash
/refine-prompt docs/prompts/migration-brief.md
```

Reads the file and treats its contents as the draft.

---

## 3. Refine the message you just wrote

```bash
/refine-prompt
```

With no argument, the previous user message becomes the draft. Useful when you type a request, realize it is underspecified, and want it sharpened before handing it to an agent.

---

## Sample session

**Input**

```bash
/refine-prompt add caching to the orders API so it's faster
```

**Step 3 — clarifying questions**

> Before I refine this, 5 questions — answer what you like, skip the rest and I'll use the defaults.
>
> 1. **Target** — Which endpoints are slow? I found `OrderController.GetById`, `GetPending` and `Search` in `src/Orders/`.
>    _Default: all read endpoints on `OrderController`, excluding writes._
>
> 2. **Success criterion** — What latency or hit-rate makes this done?
>    _Default: p99 under 200ms for cached reads, verified with the existing benchmark suite._
>
> 3. **Cache layer** — In-memory (`IMemoryCache`), distributed (Redis), or whatever the codebase already uses?
>    _Default: match the existing pattern in the repo; if none exists, `IMemoryCache`._
>
> 4. **Invalidation** — How should stale data be handled on write?
>    _Default: evict the affected key on any create/update/delete; 5-minute absolute TTL as a backstop._
>
> 5. **Scope boundary** — Anything off-limits?
>    _Default: no changes to the public API contract, no new NuGet dependencies, no changes to the persistence layer._
>
> Reply with answers, or **defaults** to accept all of them.

**User:** 1 — just `GetById` and `GetPending`. 3 — we already use Redis, see `RedisCacheService`. Rest defaults.

**Step 5 — delivery**

````
# Objective
Add read-through caching to the two hottest read endpoints on the orders API so that
repeat reads are served without hitting the database. Target: p99 under 200ms for a
cache hit.

# Context
- Project: C# / ASP.NET Core, source under `src/Orders/`.
- Endpoints in scope: `OrderController.GetById` and `OrderController.GetPending`.
- A Redis abstraction already exists at `[TBD: exact path to RedisCacheService]` — use it
  rather than introducing a new caching mechanism.
- Coding conventions are defined in `.claude/rules/csharp-conventions.md`; follow them.

# Task
1. Read `RedisCacheService` and the two target actions to understand the existing patterns.
2. Introduce read-through caching for `GetById`, keyed by order id.
3. Introduce read-through caching for `GetPending`.
4. Evict the affected cache entries on every create, update and delete path that can
   change the cached data.
5. Apply a 5-minute absolute TTL to every entry as a backstop against missed evictions.
6. Run the existing test suite and confirm it passes.

# Constraints
Must:
- Use the existing Redis abstraction.
- Propagate `CancellationToken` through every new async call.
- Keep the public API contract byte-identical — same routes, same response shapes,
  same status codes.

Must not:
- Add any new NuGet dependency.
- Modify the persistence layer or any EF Core migration.
- Cache write endpoints.
- Cache responses for authenticated requests without including the caller's identity
  in the cache key.

# Output
Modified C# source files in place. No new project, no new configuration file unless the
Redis abstraction requires a registration entry, in which case add it to the existing
DI setup.

# Acceptance criteria
- A second identical `GetById` request within the TTL performs no database query.
- Updating an order causes the next `GetById` for that id to return the new value.
- The full existing test suite passes.
- No public API signature changed.

# Edge cases and failure handling
- Cache miss or Redis unavailable → fall through to the database and serve the request
  normally. A cache outage must never turn into a request failure.
- `GetById` for a non-existent order → do not cache the negative result.
- If the existing Redis abstraction cannot support read-through without modification,
  stop and report the conflict rather than adding a second caching mechanism.
````

**What changed**

- `Vague objective` → "so it's faster" replaced with a p99 target and a stated cache-hit path.
- `Undefined scope` → narrowed from "the orders API" to two named actions.
- `Missing negative space` → added explicit do-not-touch list (API contract, migrations, dependencies).
- `Missing invalidation policy` → eviction-on-write plus TTL backstop specified.
- `Unhandled failure mode` → added Redis-unavailable fallback, which the original prompt would have left to the agent's discretion.
- `Unverifiable done` → added four checkable acceptance criteria.

**Assumptions and placeholders**

- Applied defaults for questions 2, 4 and 5 (latency target, invalidation strategy, scope boundary).
- `[TBD: exact path to RedisCacheService]` — I did not find the file; fill in the path or let me locate it.

Want me to run this prompt, tighten it further, or produce a shorter variant for a smaller model?
