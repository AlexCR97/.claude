# Type: Task

## What this type is

A task is a **bounded change that is already understood**. Someone has decided what to do; the work is doing it. There is no user whose experience changes in a way worth describing, no defect to reproduce, and no question to answer.

This is the lightest file in the directory on purpose. A task's whole risk is ceremony: running a five-round refinement and a six-phase plan over forty minutes of work costs more than the work. **The correct output for most tasks is a single phase with two or three steps.**

It is also the fallback. When a source's native type maps to nothing, the type is `task` — and the driver says so in one line rather than silently.

---

## What refine must establish

Two things, and usually nothing more:

- **The boundary.** What exactly is being changed, named concretely enough to recognise when it is done.
- **What is explicitly *not* included.** This is the question that earns its keep for a task, because tasks are where scope grows without anyone noticing.

Ask a third question only where an answer would actually change the work. If the ticket already answers both of the above, say so and skip the interview rather than manufacturing questions to fill the rounds.

---

## What digest must surface

The description and whatever passes for acceptance here — often a single sentence. Keep it short.

Omit sections the ticket does not fill. A task's digest that runs to two pages has padded, and the padding will be read as content by the plan.

---

## What shape the plan takes

**Deliverable kind:** code, usually in one place.

**Required:** nothing beyond the driver's defaults.

**Forbidden:** **do not invent phases to fill a template.** One phase is the normal answer for a task. Split into a second only when there is a genuine dependency — something that must be true before the rest can be written — not because a plan with one phase looks thin.

**Activity mix:** whatever the work actually is. A task is as likely to be Deployment or Documentation as Development.

**Estimate adjustment:** none.

---

## What done means

**The described change exists and builds.** That is the whole test.

Do not add an acceptance bar the ticket did not ask for.

---

## What implement must produce

Code changes and the driver's standard report.

Where the task turned out to be larger than its description — the boundary refine agreed on did not hold — that is worth reporting explicitly. A task that grew is usually a story or a piece of tech debt that was labelled wrong, and saying so is more useful than quietly absorbing the extra work.
