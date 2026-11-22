# Read-only scripts run without approval

_Written for the old ticket-* suite: ticketlib is now sdlclib, role files are gone (ADR 0006), and the existing store is migrated by a one-off prompt._

A script artifact that only reads runs without asking; one that writes asks first. This reverses the earlier rule that every run of every script needs approval, which made research slow without protecting anything a read could harm. Each script declares `# effect: read-only` or `# effect: writes` in its header, and the skill verifies the header against the code before running it. A header it cannot confirm, or a mismatch, falls back to asking. `ticket-resume` still runs no script, and a script declaring `# cost: heavy` or aimed at a target the config marks `sensitive` still asks.
