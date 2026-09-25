# Glossary

The words every `ticket-*` skill uses for the code a ticket's work reads and changes. Use each term exactly as defined here, and never a synonym. Two words for one thing read as two things, and the next reader has to work out whether they are.

---

## The terms

| Term                     | Meaning                                                                                                                                                                                                                                                                                                                                      |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Directory**            | A location on the machine that holds files. Every term below except *path* is a kind of directory.                                                                                                                                                                                                                                           |
| **Path**                 | The string naming a directory or a file. Always either absolute, or relative to a directory the text names.                                                                                                                                                                                                                                  |
| **Scan root**            | A directory discovery starts from. Everything in a workspace is reachable from a scan root: beneath it, or by a reference followed out of it.                                                                                                                                                                                                |
| **Default scan roots**   | The scan roots saved machine-wide by `ticket-init`, in the root `config.json`. Every plan starts from them.                                                                                                                                                                                                                                  |
| **Invocation directory** | The current directory when a skill ran.                                                                                                                                                                                                                                                                                                      |
| **Repository**           | A local git repository. Named from its remote's URL, the last segment without `.git`; where it has no remote, from its main worktree's directory name.                                                                                                                                                                                       |
| **Remote**               | A repository's hosted copy. Used to name the repository; no skill clones or fetches from it.                                                                                                                                                                                                                                                 |
| **Worktree**             | A working copy of a repository, with one branch checked out. Every repository has one **main** worktree and zero or more **linked** ones. Referred to by its repository's name, or as `{repository}@{branch}` where the workspace holds more than one worktree of that repository; git never checks one branch out twice, so that is unique. |
| **Plain directory**      | A directory in a workspace that is outside every repository. Referred to by its directory name.                                                                                                                                                                                                                                              |
| **Project**              | A directory holding one unit that is built and changed together, detected by a build or deployment file (`ticket-plan`'s signal table). It lives in one worktree or plain directory, and it is where code changes happen.                                                                                                                    |
| **Workspace**            | Everything a ticket's code work happens in: its repositories with the worktrees the work happens in, its plain directories, and the projects inside them, plus the scan roots it was found from.                                                                                                                                             |
| **Tickets home**         | The directory every ticket is stored under — `~/.tickets`, or `TICKETS_HOME`.                                                                                                                                                                                                                                                                |
| **Ticket directory**     | One ticket's directory in the tickets home: `ticket.json`, `digest.md`, `plan.md`, `journal.md`, `raw/` and `artifacts/`.                                                                                                                                                                                                                    |

---

## Rules the terms carry

- **A directory is the thing; a path is its name.** Say *directory* for the location, and *path* only for the string, stating what it is relative to. A `**Target:**` line holds a path; the argument naming where code lives takes directories.
- **A plan has exactly one workspace**, recorded in the Workspace section of `plan.md`. The skills after `ticket-plan` work in that workspace; they do not rediscover it.
- **A workspace holds only the worktrees the work happens in**, one or several per repository. Worktrees of one repository can sit on different branches with different code, so each is listed on its own, and a worktree the workspace does not list is never read or changed.
- **The workspace excludes the tickets home and every ticket directory.** Planning notes and artifacts are the ticket's record, not part of the code it changes, and neither is ever a scan root.
- **Scan roots differ in how far they are trusted.** A directory the user gave and the invocation directory are facts about this ticket: what they hold is in the workspace. A default scan root, or one found by search, says only where to look: what it holds is in the workspace when it matches the ticket.
- **Paths in `plan.md` are absolute in the Workspace section**, since that is how a later session finds the code. Everywhere else, a path is relative to its project's worktree or plain directory, and names that worktree or plain directory whenever the workspace holds more than one.

---

## Words that are not used

| Instead of                                                             | Say        |
| ---------------------------------------------------------------------- | ---------- |
| checkout                                                               | worktree   |
| service, application, module, component — as a name for a unit of code | project    |
| repo                                                                   | repository |

A retired word keeps its ordinary meaning where it names something else: the `git checkout` command, a network service to connect to, a user role such as an integrating service, a frontend UI component, a Python module, a MIME type, a ticket's *Component* field, a directory literally named `repos`.

A ticket source's own vocabulary — the repository a GitHub source reads issues from and its `--repo` flag, an Azure DevOps project — belongs to that source's provider files and never means a term above.
