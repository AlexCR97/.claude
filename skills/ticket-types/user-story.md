# Type: User Story

## What this type is

A user story asks for **new observable behaviour on behalf of someone**. What separates it from a task is the presence of a user whose experience changes: if you cannot name who notices the difference and what they can now do that they could not before, this is a task wearing a story's clothes. What separates it from a bug is that nothing is currently wrong — the behaviour simply does not exist yet.

The deliverable is working, shippable behaviour. The test for done is that someone can demonstrate it.

---

## What refine must establish

Fold these into the driver's rounds; they are the ones that cannot be skipped for this type.

**Goal and success criteria**

- **Who is the user?** A role, not "the system" — a teacher, an administrator, an integrating service. A story with no user has not been refined.
- **What can they do afterwards that they cannot do now?** Stated as an observable action, not an internal change.
- **How would we demonstrate it?** The concrete walkthrough someone would perform to accept this. If the acceptance criteria cannot be demonstrated, they are not acceptance criteria yet.
- **What is explicitly out of scope?** Stories grow during implementation; the boundary is worth agreeing before it is tested.

**Domain model and data**

- Which entities gain state, and what the new state means to the user.
- Whether any existing behaviour changes as a side effect — a story that quietly alters something already shipped is two pieces of work.

**Edge cases**

- What the user sees when the action is not permitted, and when it fails.
- Whether partial success is possible, and what the user is left with if it happens.

---

## What digest must surface

- The **user and the outcome**, in the first two sentences of the description. A digest that opens with implementation detail has buried the story.
- The **acceptance criteria**, as the demonstrable conditions they are — preferring the source's dedicated acceptance field over prose in the description when both exist.
- Any **related tickets** that carry part of the same user-visible behaviour, since a story split across tickets is only demonstrable once all of them land.

---

## What shape the plan takes

**Deliverable kind:** working code, plus the tests that show it works.

**Required:** each phase must end in something shippable. A phase that leaves the system in a state no one could demonstrate has been cut in the wrong place — prefer fewer, wider phases over a chain of phases that only mean something together.

**Forbidden:** none specific to this type.

**Activity mix:** predominantly Development, with Testing phases wherever the acceptance criteria need evidence. A Design phase earns its place only when a contract or schema has to be settled before code can be written.

**Estimate adjustment:** none specific to this type. The driver's own heuristics apply unchanged.

---

## What done means

**The acceptance criteria are demonstrable.** Not "the code is written" and not "the tests pass" — someone can perform the walkthrough refine agreed on, and see the outcome.

A criterion that cannot be demonstrated at the end is either unfinished work or a criterion that should never have been written. Say which.

---

## What implement must produce

Code changes, and a report naming the projects they touched — the driver's default.

Before reporting a phase complete, check the phase's steps against the acceptance criteria they serve. Where a phase was supposed to make a criterion demonstrable and did not, that is the finding to report, not a detail to leave to review.
