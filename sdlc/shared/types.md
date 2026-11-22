# Ticket types

The five types of work. A ticket's type is decided once at intake and recorded in `ticket.json` as `user-story`, `task`, `bug`, `spike` or `tech-debt`; a source's own type that fits none is a `task`, and the user is told. The type fixes what the work delivers, when it is done and the shape of its plan.

| Type         | Delivers                                      | Done means                                                                                              | Shapes the plan                                                                                                                                   |
| ------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `user-story` | Working behaviour with its tests              | Every acceptance criterion is demonstrable, and every child task is done                                | Each phase ends shippable. A child task tracked as its own ticket is not planned again.                                                           |
| `task`       | A bounded change that is already understood   | The described change exists and builds                                                                  | One phase of two or three steps is the normal plan; phases are not invented.                                                                      |
| `bug`        | A code change and a regression test           | The repro no longer reproduces, and a test that fails on the old code passes on the new                 | The first phase reproduces the bug and finds its cause, before any edit (Design). A fix phase follows whose first step is the failing test. No unrelated cleanup. |
| `spike`      | A written finding under `artifacts/`          | The question is answered in writing with a recommendation, a "no" included; or the timebox ended and the partial answer is stated | Design and Documentation phases only; no production code. The plan fits the timebox.                                                              |
| `tech-debt`  | A restructuring that leaves behaviour unchanged | The existing tests pass before and after, unmodified                                                  | The first phase records a baseline test run. No functional change is bundled in.                                                                  |

## Two inversions

- **A spike that changes no source file succeeded.** Its run can touch nothing but the written finding. Empty projects are never reported as a failure.
- **A tech-debt run whose tests had to be edited failed.** A changed assertion is reported and the run stops; the assertion is not fixed to make it pass. A mechanical edit (a rename, a namespace, a constructor signature) is allowed, and listed one by one. Success looks like nothing happened.

## What each type must say before it is done

Reported by `implement`, so a plan makes room for it: a bug, the cause found against the hypothesis and whether the repro was run again; a spike, the answer, the recommendation and what was not established; tech-debt, both test runs and every test file touched.
