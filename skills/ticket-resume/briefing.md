Ticket context: {context} <!-- when Step 1 adopted it: the product in backticks, then "(adopted from" the qualified reference ")" -->
Resuming {qualifiedRef} — {title}
{product} · {type} · {state} · last touched {daysAgo} days ago ({lastTouched})

The work
  <!-- 2–3 sentences from digest.md: the goal, and what done looks like -->

Where you stopped
  Phase {phaseNumber} ({phaseName}) · Step {stepId} — {stepStatus}
  <!-- the Stopped at line, or the reconstruction, labelled as one; one block per phase in flight -->

Ready now
  <!-- one line per Ready phase not yet started: "Phase N  name · ~H hrs"; each can run in a session of its own -->

Next
  {nextLine}

Progress
  <!-- one line per phase, "[x] Phase 1  name", "← in flight" on each in-flight one, "waiting on N" on the rest; collapsed per Step 6 -->
  {phasesDone} / {phaseCount} phases done · ~{hoursRemaining} hrs estimated remaining · critical path {criticalPath}

Code
  {repository} @ {branch} in {worktree} · HEAD {headSha} · {commitsAhead} commits ahead of {baseBranch}
  Worktree state: {worktreeState}
  {baseBranch} has moved {baseCommitsNotMerged} commits since you branched
  {stashCount} stash(es): {stashSubject}

Carried forward
  <!-- one line each: "• decision — why (Step N.M)", "• Blocker: what — what would clear it (Step N.M)", "• Question: what — who can answer (Step N.M)" -->

Changed while you were away
  <!-- "• field: before → after" per change, and "• N new comments — author, N days ago: \"snippet\"" -->
  → <!-- Step 5's fetch-and-digest recommendation -->

Ready to continue. I can:
  • `/ticket-implement {qualifiedRef} {phaseNumber}` — pick up Phase {phaseNumber} where it stopped
  • `/ticket-implement {qualifiedRef} {readyPhaseNumber}` — start Ready Phase {readyPhaseNumber}, here or in a session of its own
  • `/ticket-fetch {qualifiedRef}` then `/ticket-digest {qualifiedRef}` — fold in the changes first
  • `/ticket-plan {qualifiedRef}` — review or revise the plan before continuing

Or tell me what you would rather do.
