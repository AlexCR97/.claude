# Test-driven development

Read by `ticket-plan` (*Planning*) and `ticket-implement` (*Implementing*); each reads only its own section. Test-first is the preferred way to change behaviour: a phase is a TDD phase wherever the work fits, and `Development` and `Testing` cover the work it does not fit. The terms — TDD phase, seam, slice, red, green, test project, test-setup phase — mean what [`GLOSSARY.md`](./GLOSSARY.md) says.

Condensed from `mattpocock-skills:tdd`, and self-contained so it holds on a machine without that plugin.

---

## Planning

### When a phase is a TDD phase

Both gates must pass:

1. **The type allows it.** The resolved type file's activity mix names `TDD` for this kind of work, and nothing in it forbids `TDD`.
2. **The work has a seam.** The phase changes behaviour a caller can observe at a seam, and a test project in the workspace can exercise that code — or a test-setup phase will create one.

Work that passes the first gate but has no seam — configuration, pipelines, IaC, migrations, dependency-injection wiring, markup, documentation — is `Development`, with a `Testing` phase where it needs test-after coverage. A phase mixing both kinds is split so the TDD part stands on its own.

### Proposing seams

For each TDD phase, from the targeted read of its projects, propose the seams its tests will sit at. Each seam names its public interface and carries one line on what testing there catches and what it misses. Aim the seams at the acceptance criteria and at complex logic; a seam per edge case spreads the effort thin.

### Offering a test-setup phase

Where a phase passes the first gate and has a seam, but no test project can exercise its code, offer a test-setup phase:

- **Activity:** `Testing`, placed immediately before the first TDD phase that needs it.
- **Framework:** the one the repository already uses in another test project. Where it uses none, ask which, and record the answer.
- **Steps:** create the test project, reference the project under test, and register it wherever the repository lists its projects (a solution file, a workspace manifest).
- **Done:** the test project builds and its runner executes. A run that finds no tests counts.
- **Approval:** confirming the phase approves the packages it adds.

### The seam checkpoint

Ask once, covering every TDD phase: its seams, and any test-setup phase offered. Wait for the answer, then apply it:

- **A confirmed seam** is recorded on the `**Seam:**` line of each step that tests at it.
- **A rejected seam** drops its slices. A TDD phase left with no seam becomes `Development`.
- **A declined test-setup phase** turns every phase that needed it into `Development`, with no `Testing` phase for it.

### Shaping a TDD phase's steps

Each step is one slice, ordered as tracer bullets: the first drives the thinnest path end to end through its seam, and each later one adds a case to what the last proved. A step carries:

- **`**Target:**`** — the test file, then the production file.
- **`**Seam:**`** — the confirmed seam the test sits at.
- **Its body** — the behaviour the test asserts, in the words of a specification ("an expired invitation is rejected"), and where its expected value comes from: a literal, a worked example, the spec.

Every step pairs its test with the production code that turns it green.

---

## Implementing

### The loop, one step at a time

1. **Red.** Write the step's one test at its seam. Run that test alone (by file or filter, per `BUILD-COMMANDS.md`). It fails on the missing behaviour; a failure from a typo, a broken fixture or a missing reference is fixed until the failure is the behaviour itself.
2. **Green.** Write the least production code that makes it pass. Run the test again, then its whole test file.
3. **Say it.** State in chat the test's name, its red failure message, and its green result.
4. **Record it.** Keep the step's `**Status:**` note current with the slice's state.

A test that passes on its first run means the behaviour already exists, or the test misses it. Say which. Where the test misses it, rewrite the test until it goes red. Where the behaviour exists, keep the test as coverage and mark the step `Done` with a note saying so.

Refactoring sits outside the loop. Green code stays as written unless a later slice needs it changed; the developer's review is where structure gets improved.

### A test worth keeping

- **It verifies behaviour through the seam's public interface**, and reads like a specification: its name says *what* the caller gets, not *how* the code does it. It survives a refactor that keeps the behaviour.
- **Its expected value is independent of the code**: a known literal, a worked example, the spec — never recomputed the way the production code computes it.
- **It observes through the interface.** A value written through the seam is read back through the seam, not through a side channel such as a database query.
- **It mocks only system boundaries**: external APIs, time, randomness, and sometimes the database or file system. The project's own classes run for real.
- **It holds one logical assertion.**

### Test runs

- **Each cycle:** the single test, then its file — as the loop says.
- **At the end of every phase that changed code** (`TDD`, `Testing` or `Development`): after the build, the full suite of each test project that covers code the phase touched, using `BUILD-COMMANDS.md`. A `Development` phase with no covering test project runs none.
- **A failing suite** is handled as a build failure: one fix attempt, then stop and report.

### When a seam does not fit

A confirmed seam that turns out not to exist, or not to reach the behaviour, stops the step. Set it `Blocked` with a note naming the seam and why it fails, and ask where the test should sit instead. Planning confirmed the seams; this is the one case implementation asks again.
