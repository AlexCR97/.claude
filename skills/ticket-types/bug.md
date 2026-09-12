# Type: Bug

## What this type is

A bug is **behaviour that already exists and is wrong**. The distinguishing feature is that the system is doing something today, and the work is making it stop. That gives a bug two properties nothing else in this directory has: there is a reproduction, and there is a cause that is not yet known.

Both matter more than they look. Work that skips the reproduction fixes a symptom; work that skips the cause fixes one path out of three.

---

## What refine must establish

These are the round-one questions for a bug, and none of them is optional:

- **Repro steps.** The exact sequence that produces the wrong behaviour, including the starting state. "Sometimes it fails" is not a repro; establishing what makes it sometimes is part of refinement.
- **Expected versus actual.** Both, stated separately. A report that only says what happened has not said what should have happened, and those are frequently not the same disagreement.
- **Environment.** Where it reproduces and where it does not — which build, which configuration, which data. A bug that reproduces in one environment and not another has already told you half the cause.
- **A root-cause hypothesis.** Not a commitment; a starting point, with what would confirm or kill it. Recording the hypothesis is what stops the first investigation phase from starting cold.

Then the usual rounds. In edge cases, ask specifically: **is the wrong behaviour also happening somewhere nobody has looked?** Bugs rarely have exactly one entry point.

---

## What digest must surface

- **The repro steps, first.** Where the source carries a dedicated reproduction field, **prefer it over the description** — the description on a bug is often the reporter's narrative, while the repro field is the part that can be executed.
- **Expected versus actual**, side by side.
- **The environment** where it reproduces.
- **The root-cause hypothesis**, clearly labelled as a hypothesis.
- Any **attachment that is evidence** — a stack trace, an error screenshot, a log — described for what it shows, not merely listed.

---

## What shape the plan takes

**Deliverable kind:** a code change, plus a test that fails before it and passes after.

**Required — the first phase reproduces and localizes, before anything is changed.** Its steps confirm the repro, narrow it to the code path responsible, and record what was found. Only then does a phase change anything. A plan whose first phase edits code has assumed the cause, and the estimate on every later phase is resting on that assumption.

**Required — a phase that adds regression coverage.** A bug with no test is a bug scheduled to return.

**Forbidden:** bundling unrelated cleanup into the fix. Whatever else the investigation turns up is its own ticket; a fix diff that also refactors cannot be reviewed for the thing it was meant to do.

**Activity mix:** the first phase is Design (it is investigation, not code), then Development for the fix, then Testing for the regression coverage.

**Estimate adjustment:** **where the root cause is unclear, add a +1 hour investigation buffer** to the first phase. "Unclear" means refine produced a hypothesis nobody could confirm, or produced none at all. Where the hypothesis is confirmed and the cause is already localized, do not add it.

---

## What done means

Two conditions, both required:

1. **The repro no longer reproduces.** Run the exact steps refine recorded, not an approximation of them.
2. **A regression test covers it** — one that fails against the old behaviour and passes against the new.

A fix that satisfies only the first is a fix that will be undone by someone who never knew it happened.

---

## What implement must produce

Code changes, the regression test, and the driver's standard report.

Two additions to the report for this type:

- **State what the cause turned out to be**, and whether it matched the hypothesis. Where it did not, say what it was instead — that correction is the most valuable thing the run produced, and the ticket's description still asserts the wrong thing until someone says so.
- **Say whether the repro was actually re-run**, and what it did. "The fix is implemented" is not the same claim as "the bug is gone", and only one of them is the completion test.
