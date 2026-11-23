# Protected branches are read and fast-forward only

_Written for the old ticket-* suite: ticketlib is now sdlclib, role files are gone (ADR 0006), and the existing store is migrated by a one-off prompt._

Ticket skills may run any git or `gh` operation except one that writes to a protected branch: no commit, push, force-push, non-fast-forward merge, rebase, reset, cherry-pick onto it, or file edit in a worktree that has it checked out. Fetching and fast-forwarding it from its remote are allowed, because a ticket branch cut from an up-to-date default branch is the clean state implementation needs. The earlier rule, no git at all in `ticket-implement`, was safe but made branch and worktree creation impossible. A shared guard in `ticketlib` enforces the policy, not prose in each skill, so one definition of "protected" covers every skill.
