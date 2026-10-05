# Graph rules

How `ticket-plan` cuts a ticket's work into phases and draws the dependencies between them. Read by `SKILL.md` Step 11, and by `MIGRATION.md` when it re-derives the dependencies of a converted plan.

A phase is the unit one session works: it is cut so it can be implemented, built and verified **on its own**, and the graph between phases is what lets several sessions work at once.

---

## Cutting phases

- A phase delivers something that builds and checks out by itself. A step that will not compile without another phase's steps belongs with them, or after them.
- Where the type file says a plan of this kind is normally a single phase, do not invent phases to fill a graph.
- Where a phase's work spans more than one Activity, `SKILL.md` Step 10 already decided whether to split it.

## Prerequisites

Something that must be in place before a phase starts, but that is not work the phase does — an environment variable in every target environment, a feature flag, a package in the internal feed, an access granted.

- **Needed by one phase** → that phase's own `## Prerequisites` checklist.
- **Shared by two or more phases** → phase `0`, `0-prerequisites.md`: an ordinary phase, usually a single step, estimated at **~1 hr at most**, with the closest Activity from `SKILL.md` Step 10's set — usually Deployment, or Human Review where the item is a decision or an approval. Only the phases that need it depend on it. A plan with no shared prerequisite has no phase `0`.

Per `ticket-common/STATUS.md` → *Ready is derived too*, a phase is not Ready until its own prerequisites are checked and every phase it depends on — phase `0` included — is `Done`.

## Drawing dependencies

**Phase B depends on phase A only when B cannot be written or built without A's output** — a schema, a contract, a type, an endpoint, a shared library version it consumes. A sensible order is not a dependency: tests depend on the code they exercise, not on everything before them, and documentation on what it documents. Every dependency drawn costs parallelism; draw only the real ones.

The usual flow of output, as guidance for spotting them — each item depends on whichever earlier one it actually consumes:

1. Design — schema, API contracts, architecture decisions
2. Database / schema changes
3. Backend — data access, then business logic, then API
4. Shared libraries or contracts (if updated)
5. Frontend — on the API it calls
6. Tests — on the code they exercise
7. Documentation — on what it documents
8. DevOps / CI / deployment — on what it deploys

A Human Review phase gates the phases that consume what it reviews: they depend on it, and it depends on the phase whose output it reviews.

**Two phases that edit the same file must be joined by a dependency, or merged.** Phases with no path between them are claimed parallel-safe, and two sessions editing one file at once will collide. `plan-sync` warns about every pair of phases sharing a `**Target:**` with no path between them; resolve each warning before finishing.

The type file wins over all of this: a phase it requires to come first is a root that every phase it names depends on, and a phase or dependency it forbids is not drawn. The graph must be acyclic — `plan-sync` refuses one that is not.

## Numbering

Number the phases `1`, `2`, `3`, … in **topological order**: every phase after all the phases it depends on. One digit per number, never padded — `1-database-migration.md`, `Step 3.2`, `artifacts/step-3.2/`. Where two phases have no path between them, break the tie by the flow above, then by estimate, larger first. Phase `0` is reserved for shared prerequisites and never takes part in the ordering.
