# Type: Spike

## What this type is

A spike is **a time-boxed question, not a change**. Its deliverable is a written finding: an answer, a recommendation, and enough evidence that the next person does not have to redo the investigation. Code may be written along the way, but throwaway code is a *means* here, never the outcome.

Everything awkward about this type follows from one fact: **the run can succeed while touching no source file at all.** A spike that ends with a document and no code change is a finished spike, and any machinery that reads "no projects touched" as failure will get this exactly backwards.

---

## What refine must establish

Four things. A spike that starts without all four will run until someone notices it has no end condition.

- **The exact question.** Narrow enough to be answered yes or no, or with a named choice. "Investigate caching" is not a question; "can we serve the authorization lookup from a per-request cache without changing what callers see?" is.
- **The timebox.** In hours, agreed up front. The timebox is the deliverable's deadline, not an estimate of how long the truth takes — reaching the box with a partial answer is a valid outcome, and the finding says so.
- **The artifact that ends it.** Which document, holding what: a comparison, a recommendation, a measurement, a prototype's results. The spike is over when that file exists, not when the investigator feels informed.
- **The decision it unblocks.** Who is waiting for this, and what they will do differently depending on the answer. A spike no decision depends on should not run.

In later rounds, ask what evidence would be strong enough to settle the question — that answer is what the plan's phases are built out of.

---

## What digest must surface

- **The question and the timebox**, at the top, before anything else.
- **The decision waiting on it**, and who is waiting.
- **The artifact that ends it**, named.
- What has already been ruled in or out, so no phase re-establishes it.

Acceptance criteria on a spike, where the source has such a field at all, usually describe the finding rather than a behaviour. Surface them as what they are.

---

## What shape the plan takes

**Deliverable kind: a written finding under `artifacts/`.** Every phase's output is a file, not a source change. A step whose target is a path in the repository has misread the type.

**Required:** each phase is an investigation with a stated question of its own and a named artifact that answers it. The final phase writes the recommendation — including the case where the recommendation is "do not do this".

**Required:** the plan's total estimate must fit inside the timebox. Where the phases do not fit, say so and cut scope before writing the plan, rather than producing a plan that was over budget the moment it was written.

**Forbidden:** production code changes. **Forbidden: an Activity of Development on any phase** — the activity mix is Design and Documentation, and nothing else. A prototype written to answer the question is an artifact, and it lives under `artifacts/`, so its phase is still Design.

**Estimate adjustment:** the timebox is the cap. Where an investigation is open-ended, phase it so the most decisive evidence is gathered first — a spike that runs out of time having answered the main question beats one that ran out having prepared to answer it.

---

## What done means

**The question is answered in writing, with a recommendation.**

**Including when the answer is "no".** A spike that concludes the approach does not work has succeeded — it has saved the cost of finding out during implementation, which is the entire reason the spike was run. Report that outcome with the same finality as a "yes".

A spike that reaches its timebox without a conclusive answer is also done, provided the finding says what was established, what was not, and what it would take to settle the rest. What is not done is a spike with nothing written down.

---

## What implement must produce

**A document-only outcome is success, not an incomplete step.** This is the rule that matters most in this file.

The run produces the artifacts the phases named, under `artifacts/`, and reports each phase `Done` on that basis. Do not report a missing code change, do not list touched projects as empty and imply something went wrong, and do not leave a step `In Progress` because nothing was compiled. There was nothing to compile; that is what this type is.

The completion report for a spike says:

- **The answer**, in one or two sentences, up front.
- **The recommendation**, and what it is based on.
- **The artifact paths** holding the evidence.
- **What was not established**, where the timebox ran out before the question was fully settled.

Where the investigation produced throwaway code, say plainly that it is throwaway and where it lives, so nobody later mistakes an artifact for a deliverable.
