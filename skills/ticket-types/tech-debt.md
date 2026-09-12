# Type: Tech Debt

## What this type is

Tech debt is **restructuring that must leave behaviour unchanged**. The system already does the right thing; it does it in a shape that is expensive to work in. The work changes the shape and nothing else.

The defining constraint is the one that makes this type hard to verify: **success looks like nothing happened.** There is no new behaviour to demonstrate and no defect to stop reproducing, so the only available proof is that the existing tests still pass — *unmodified*. Everything below follows from that.

---

## What refine must establish

- **The current structure.** What is there now, concretely: the classes, the flow, the duplication, the coupling. Named, not characterised.
- **The target structure.** What it should look like afterwards, in the same terms, so the difference is inspectable rather than a matter of taste.
- **The blast radius.** Everything that calls into what is being restructured — including anything outside this codebase that depends on a signature, a contract, or a wire format. A refactor whose radius was underestimated is the most common way this type goes wrong.
- **What proves behaviour is unchanged.** The single most important answer in the interview. Which tests, which characterization, which measurement. **Where the answer is "nothing covers this today", that is the first phase of the plan**, not a caveat.

Ask also: what is explicitly *not* being changed? Tech debt tickets attract passengers, and every functional change bundled into one destroys the property that makes it verifiable.

---

## What digest must surface

- **Current structure and target structure**, side by side.
- **The blast radius**, as a list of what is affected.
- **The behaviour-unchanged invariant**, stated as the acceptance condition it is — surfaced even where the ticket's own acceptance field is empty, because it always holds for this type whether or not anyone wrote it down.
- The **motivation**: what this makes cheaper or safer afterwards. A refactor with no stated payoff is a preference.

---

## What shape the plan takes

**Deliverable kind:** a code change with no behavioural difference, plus whatever test coverage was needed to prove that.

**Required — the first phase captures the existing behaviour under test.** Before anything is restructured. Where coverage already exists and is adequate, the phase confirms it runs green and records what it covers; where it does not, the phase writes it. Either way the baseline exists before the first structural edit, because after that edit there is no way to establish what the old behaviour was.

**Required:** phases sequenced so the system is working at the end of each. A refactor left half-applied across a session is worse than one not started.

**Forbidden — no functional change may be bundled in.** Not a fix noticed along the way, not a small improvement, not a rename that alters a public contract. Each of those is a separate ticket. If one turns out to be unavoidable, stop and say so rather than folding it in.

**Activity mix:** Testing for the characterization phase, then Development for the restructuring, then Testing again where coverage needed to move with the code.

**Estimate adjustment:** scale with the blast radius, not with the size of the thing being restructured. Ten call sites in three services costs more than a thousand lines in one file.

---

## What done means

**Behaviour unchanged, structure improved.**

The test: **the existing tests pass before and after, unmodified.**

The word *unmodified* is the whole of it. A test that had to be edited to keep passing has recorded a behaviour change — the assertion that had to move is naming exactly what moved with it. That is a finding, not a chore.

A test may legitimately be edited for structural reasons alone: a renamed type, a moved namespace, a changed constructor signature the test calls. Those are mechanical and must be called out as such, one by one. **An edit to an assertion is never mechanical.**

---

## What implement must produce

The restructuring, the baseline test run from the first phase, and the same run afterwards.

**A behaviour change is a failure to report and stop on, not a side effect to accept.** Where the tests do not pass unmodified after the restructuring:

1. **Stop.** Do not continue to the next phase.
2. Report which test, what it asserted, and what the new behaviour is instead.
3. Ask whether to revise the approach or revise the plan. Do not edit the assertion to make it pass.

**If a test had to be edited to pass, that is the finding.** Report it in those terms, even where the edit looks trivially correct — especially then, because a change that looks obviously fine is the one that ships unnoticed.

The completion report for this type adds:

- **The test result before and after**, both stated, so "unchanged" is evidenced rather than claimed.
- **Every test file that was touched**, each with the reason, separated into mechanical edits and anything else. Where the second list is not empty, the phase is not done.
