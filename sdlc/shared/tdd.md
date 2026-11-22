# Test-driven development

The one-page TDD note kept in the plugin (see ADR 0005). `plan` reads *Planning*; `implement` reads *Implementing*. Terms (TDD phase, seam, slice, red, green, test project, test-setup phase) mean what [`GLOSSARY.md`](../GLOSSARY.md) says. Where the plan's phases and steps are recorded is [`plan.md`](./plan.md).

## Rules

1. **Confirm the seams with the user** before any TDD step is planned. A seam is a public method, an endpoint, a command handler or a component's rendered output. Tests sit at confirmed seams only.
2. **One slice per step.** A slice is one test at one seam plus the least production code that makes it pass. The first slice is the thinnest path end to end; each later one adds a case to what the last proved.
3. **A test fails first, for the right reason.** Red means the missing behaviour itself fails the test, not a typo, a broken fixture or a missing reference. Then it passes.
4. **A test observes behaviour through the public boundary.** What it writes through the seam it reads back through the seam, and its expected value is a literal or a worked example, never recomputed the way the code computes it. Only system boundaries are faked (external APIs, time, randomness, sometimes the database or file system); the project's own classes run for real.

## Planning

**A phase is a TDD phase when both hold:** the work changes behaviour a caller can observe at a seam, and a test project can exercise that code (or a test-setup phase will create one). Work with no seam is `Development`, or `Documentation`: configuration, pipelines, infrastructure, migrations, wiring, markup, spikes. A phase mixing both is split, and the plan says in the phase why it is not TDD.

**Propose seams** per TDD phase from reading its projects: each names its public interface and one line on what testing there catches and what it misses. Aim them at the acceptance criteria and at complex logic; a seam per edge case spreads effort thin.

**Test-setup phase.** Where a TDD phase needs a test project and none can exercise its code, the plan opens that part with a `Testing` phase placed right before the first TDD phase that needs it. Its steps create the test project, reference the project under test, and register it wherever the repository lists its projects. It uses the framework the repository already uses elsewhere; where there is none, ask which. Done means the project builds and its runner executes; a run that finds no tests counts.

**The seam checkpoint.** Ask once, covering every TDD phase: its seams, and any test-setup phase. Wait for the answer. A rejected seam drops its slices, and a TDD phase left with no seam becomes `Development`. A declined test-setup phase turns the phases that needed it into `Development`. Record what was confirmed in the plan before estimating.

**Shape a TDD phase's steps** as slices: the `**Target:**` names the test path, then the production path; the `**Seam:**` names the confirmed seam; the body states the behaviour the test asserts in the words of a specification ("an expired invitation is rejected") and where its expected value comes from.

## Implementing

For each step, in order:

1. **Red.** Write the step's one test at its seam and run it alone. It fails on the missing behaviour; fix any other failure until the failure is the behaviour itself.
2. **Green.** Write the least production code that passes it. Run the test again, then its file.
3. **Say it.** State the test's name, its red failure message and its green result; keep the step's status note current.

A test that passes on its first run means the behaviour exists or the test misses it: say which. Rewrite a test that misses; keep one for behaviour that exists and mark the step `Done` with a note. Refactoring is outside the loop. At the end of a phase that changed code, run the full suite of each test project covering code the phase touched. A confirmed seam that does not exist or does not reach the behaviour sets the step `Blocked` with a note and asks where the test should sit: the one case where implementation asks again.
