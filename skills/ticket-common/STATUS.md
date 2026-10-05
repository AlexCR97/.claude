# Step status

The four-value vocabulary a plan records progress in, on the steps of each phase file under `plan/`. Read by `ticket-plan`, `ticket-implement` and `ticket-checkpoint` — all three write these lines, so all three read the same 60 lines rather than one of them loading a 400-line driver to learn them.

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

A phase file has no status of its own — not in its frontmatter, not anywhere. `ticket.py plan-sync` computes it from the phase's steps and writes it into the Progress table in `plan/plan.md`:

| Condition | Phase status |
| --- | --- |
| Any step `Blocked` | `[!] Blocked` |
| Every step `Done` | `[x] Done` |
| Any step `Done` or `In Progress` | `[~] In Progress` |
| Otherwise | `[ ] Pending` |

The script adds a parenthetical where the status alone misleads — the blocked step's id, or how many steps are done.

A phase whose steps are not all `Done` is not `[x] Done`, however much of it ran. The point of the derivation is that the table cannot claim more than the steps support — and since a script derives it, no skill can claim more by hand.

**Never edit the Progress table.** Change a step's `**Status:**` line in its phase file, then run `ticket.py plan-sync`. The table sits in a generated block that every sync rewrites in full from the phase files, so whichever session syncs last writes the correct state for all of them.

---

## Ready is derived too

A phase is **Ready** when every phase in its `depends_on` is `Done` and every item in its own `## Prerequisites` is checked. The Progress table's Ready column shows ✅, or why not — `waiting on 2`, `1 prerequisite open`.

Ready is never written down. A recorded "waiting" would go stale the moment the dependency finished, and keeping it current would mean re-editing every phase downstream of it.

**Waiting is not `Blocked`.** `Blocked` means something outside the graph stops the work — an answer, an access, a contradiction — and carries a note saying what. A phase whose dependency is unfinished is simply not Ready yet, and neither is one whose dependency is `Blocked`. A `Blocked` phase itself is never Ready.

---

## Where the *why* goes

A status note records **what** state a step is in. **Why** it is in that state belongs in `journal.md`, and `ticket-checkpoint` is the only skill that writes it. Keep the note to one line and let the journal carry the account.
