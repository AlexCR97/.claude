# Step status

The four-value vocabulary `plan.md` records progress in. Read by `ticket-plan`, `ticket-implement` and `ticket-checkpoint` — all three write these lines, so all three read the same 40 lines rather than one of them loading a 400-line driver to learn them.

---

## The four values

A step's `**Status:**` line takes exactly one of four values, optionally followed by ` — ` and a one-line note:

| Status | Means | Note |
| --- | --- | --- |
| `Pending` | Not started | None |
| `In Progress` | Started, not finished | **Required** — what is done and what remains |
| `Blocked` | Cannot proceed | **Required** — what is blocking, and what would clear it |
| `Done` | Finished | Optional — only where the outcome differed from what the step asked for |

```
**Status:** In Progress — harness runs for the Analytics job; the Identity case throws at startup
**Status:** Blocked — waiting on the Identity team to confirm the claim name
```

`Pending` and `Done` are the only two statuses a freshly generated plan may use — nothing has been started yet, so nothing can be in progress or blocked.

`In Progress` and `Blocked` exist so that stopping mid-phase is recordable. A session that ends between steps must leave the plan saying so: a step that is 80% finished marked `Pending` loses the 80%, and marked `Done` loses far more than that.

**Never write a bare `In Progress` or `Blocked`.** The note is what makes the state actionable in a later session — `In Progress` on its own says only that a step was touched, which is nearly as unhelpful as `Pending`. Keep it to one line; the fuller account of a session belongs in `journal.md`, which `ticket-checkpoint` writes.

---

## A phase's status is derived, never set

The phase's row in the Progress table is computed from its steps:

| Condition | Phase status |
| --- | --- |
| Any step `Blocked` | `[!] Blocked` |
| Every step `Done` | `[x] Done` |
| Any step `Done` or `In Progress` | `[~] In Progress` |
| Otherwise | `[ ] Pending` |

A phase row may carry a short parenthetical where the count alone misleads — `[x] Done (4 skipped)`, `[~] In Progress (2.7 left to run)`.

A phase whose steps are not all `Done` is not marked `[x] Done`, however much of it ran. The point of the derivation is that the table cannot claim more than the steps support.

---

## Where the *why* goes

A status note records **what** state a step is in. **Why** it is in that state belongs in `journal.md`, and `ticket-checkpoint` is the only skill that writes it. Keep the note to one line and let the journal carry the account.
