# TDD guidance is kept in the plugin and trimmed to one page

`implement` works test-first in TDD phases, and the plugin carries its own one-page TDD note instead of delegating to `mattpocock-skills:tdd`: confirm the seams with the user, one slice per step, and a test must fail first for the right reason. The note is tied to the plan's seams, steps and status vocabulary, which no outside skill knows about, and the plugin must work when no other plugin is installed.

We rejected delegating to the `mattpocock-skills` TDD skill. It would make the plugin's behaviour depend on another plugin's installation and version, and its loop does not record seams or step statuses in `plan.md`. The cost is that our note can drift from upstream's thinking; trimming it to one page keeps it cheap to revisit.
