# Glossary

The words every `ticket-*` skill uses for where tickets are kept and for the code a ticket's work reads and changes. Use each term exactly as defined here, and never a synonym. Two words for one thing read as two things, and the next reader has to work out whether they are.

---

## The terms

### Where tickets are kept

| Term                    | Meaning                                                                                                                                                                                                                                                                                                                      |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tickets home**        | The directory every ticket is stored under — `~/.tickets`, or `TICKETS_HOME`. It holds the root `config.json`, the credential store `.credentials/`, and one directory per namespace.                                                                                                                                        |
| **Namespace**           | The top level of the tickets home: one body of work that must never mix with another, such as an employer, a client or personal work. Holds products. Its binding holds each source's namespace-level coordinate: an Azure DevOps organization, or a GitHub owner.                                                           |
| **Product**             | A body of work inside a namespace that tickets are filed under, such as EW.Educate or a notes app. Holds one directory per source. Its binding holds each source's product-level coordinate: an Azure DevOps project, or a GitHub repository.                                                                                |
| **Fallback product**    | A namespace's product named `default`, where a ticket is filed when its namespace is known but no product fits it — including when the namespace's default product is bound to other coordinates. `default/default`, the fallback product of the namespace named `default`, receives a ticket that no namespace fits either. |
| **Default namespace**   | The namespace a new ticket is filed under when neither the ticket nor the session context decides: the one the root `config.json` names in `default_namespace`, else the namespace named `default`.                                                                                                                          |
| **Default product**     | The product a namespace files a new ticket under when nothing else decides: the one its `config.json` names in `default_product`, else its fallback product.                                                                                                                                                                 |
| **Session context**     | The namespace, and optionally the product, a conversation chose with `/ticket-context`. It decides which ticket a reference means first and where a new ticket is filed; it changes nothing about a ticket already filed.                                                                                                    |
| **Coordinates**         | The values that locate a ticket in its source, named by that source's `provider.json`: an organization and a project, an owner and a repository. `ticket.json` records a ticket's own, and they win over any binding.                                                                                                        |
| **Binding**             | The coordinates a namespace or product records for one source, under `sources.{source}` in its `config.json`. New tickets are fetched with them, and a pasted address is filed by them.                                                                                                                                      |
| **Effective config**    | The root, namespace and product `config.json` merged, the inner level winning. Every skill reads this, never one file alone.                                                                                                                                                                                                 |
| **Filing**              | Choosing the product a ticket not yet on disk is placed under, by the rules in `RESOLUTION.md`: first which products can hold it, then which of them the session context, the invocation directory or the default product prefers. Moving it later with `/ticket-move` is re-filing.                                         |
| **Ticket directory**    | One ticket's directory, at `{namespace}/{product}/{source}/{id}` in the tickets home: `ticket.json`, `digest.md`, `plan.md`, `journal.md`, `raw/` and `artifacts/`.                                                                                                                                                          |
| **Qualified reference** | `{namespace}/{product}/{source}:{id}` — names one ticket on the machine without ambiguity.                                                                                                                                                                                                                                   |

### The code a ticket touches

| Term                     | Meaning                                                                                                                                                                                                                                                                                                                                      |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Directory**            | A location on the machine that holds files. Every term in this table except _path_ is a kind of directory.                                                                                                                                                                                                                                   |
| **Path**                 | The string naming a directory or a file. Always either absolute, or relative to a directory the text names.                                                                                                                                                                                                                                  |
| **Scan root**            | A directory discovery starts from. Everything in a workspace is reachable from a scan root: beneath it, or by a reference followed out of it.                                                                                                                                                                                                |
| **Default scan roots**   | The scan roots saved by `ticket-setup` in a `config.json` — the root's, a namespace's or a product's. A plan starts from the effective list of the ticket's product: the nearest level that sets one.                                                                                                                                        |
| **Invocation directory** | The current directory when a skill ran.                                                                                                                                                                                                                                                                                                      |
| **Repository**           | A local git repository. Named from its remote's URL, the last segment without `.git`; where it has no remote, from its main worktree's directory name.                                                                                                                                                                                       |
| **Remote**               | A repository's hosted copy. Used to name the repository; no skill clones or fetches from it.                                                                                                                                                                                                                                                 |
| **Worktree**             | A working copy of a repository, with one branch checked out. Every repository has one **main** worktree and zero or more **linked** ones. Referred to by its repository's name, or as `{repository}@{branch}` where the workspace holds more than one worktree of that repository; git never checks one branch out twice, so that is unique. |
| **Plain directory**      | A directory in a workspace that is outside every repository. Referred to by its directory name.                                                                                                                                                                                                                                              |
| **Project**              | A directory holding one unit that is built and changed together, detected by a build or deployment file (`ticket-plan`'s signal table). It lives in one worktree or plain directory, and it is where code changes happen.                                                                                                                    |
| **Workspace**            | Everything a ticket's code work happens in: its repositories with the worktrees the work happens in, its plain directories, and the projects inside them, plus the scan roots it was found from.                                                                                                                                             |

---

## Rules the terms carry

- **A ticket is filed under exactly one product. Filing organizes; coordinates identify.** Re-filing a ticket never changes where it lives upstream, and where it is filed is never written into the ticket: the directory is the record of that.
- **Namespace and product names are lowercase slugs.** `default` is reserved for the fallback products, and a name starting with `.` is never a namespace or a product. A provider's own spelling — `EW.Educate` — belongs in a binding, never in a directory name.
- **Two products are never bound to the same coordinates**, or a pasted address could be filed in two places. A fallback product is never bound at all: it holds what no binding fits.
- **The default product and the session context never file a ticket against its coordinates, and the default product never decides which existing ticket a reference means.** A wrong filing is visible and one `/ticket-move` from fixed; a wrong resolution attaches a session's work to the wrong ticket.
- **A reference stored in a ticket is short within its own product and qualified across products**, because it is resolved from its own ticket's product first.
- **A directory is the thing; a path is its name.** Say _directory_ for the location, and _path_ only for the string, stating what it is relative to. A `**Target:**` line holds a path; the argument naming where code lives takes directories.
- **A plan has exactly one workspace**, recorded in the Workspace section of `plan.md`. The skills after `ticket-plan` work in that workspace; they do not rediscover it.
- **A workspace holds only the worktrees the work happens in**, one or several per repository. Worktrees of one repository can sit on different branches with different code, so each is listed on its own, and a worktree the workspace does not list is never read or changed.
- **The workspace excludes the tickets home and every ticket directory.** Planning notes and artifacts are the ticket's record, not part of the code it changes, and neither is ever a scan root.
- **Scan roots differ in how far they are trusted.** A directory the user gave and the invocation directory are facts about this ticket: what they hold is in the workspace. A default scan root, or one found by search, says only where to look: what it holds is in the workspace when it matches the ticket.
- **Paths in `plan.md` are absolute in the Workspace section**, since that is how a later session finds the code. Everywhere else, a path is relative to its project's worktree or plain directory, and names that worktree or plain directory whenever the workspace holds more than one.

---

## Words that are not used

| Instead of                                                             | Say             |
| ---------------------------------------------------------------------- | --------------- |
| checkout                                                               | worktree        |
| service, application, module, component — as a name for a unit of code | project         |
| repo                                                                   | repository      |
| project, board, space — as a name for a group of tickets               | product         |
| organization, owner, account — as a name for a namespace               | namespace       |
| context, on its own, for the session's namespace and product           | session context |

A retired word keeps its ordinary meaning where it names something else: the `git checkout` command, a network service to connect to, a user role such as an integrating service, a frontend UI component, a Python module, a C# or XML namespace, a MIME type, a ticket's _Component_ field, a directory literally named `repos`, the context a session has loaded.

A ticket source's own vocabulary — the repository a GitHub source reads issues from and its `--repo` flag, an Azure DevOps organization or project — belongs to that source's provider files and never means a term above. In a binding it is a coordinate: never a namespace, a product or a project.
