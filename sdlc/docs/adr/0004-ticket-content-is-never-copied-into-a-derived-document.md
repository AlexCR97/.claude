# Ticket content is never copied into a derived document

The suite used to write a `digest.md` for every ticket: an AI-written second copy of a ticket whose source of truth is upstream. It could drift from the source, it cost an extra step, and every later skill trusted it instead of the ticket. The plugin writes no digest. A remote ticket is brought in as a **mirror**, a refreshable cache in `raw/` that is never authoritative; a local ticket's own file is its source of truth. `plan` and `implement` read the mirror or that file directly, and `resume` compares the ticket's current revision with the one recorded at mirroring instead of re-reading content.

We rejected keeping the digest as a cache that is refreshed on demand. Any derived copy that a skill reads in place of the ticket can contradict it, and a refresh rule only moves the question to whether the rule ran. Reading the mirror directly costs a few more tokens per skill, which we accept.
