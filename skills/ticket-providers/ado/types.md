# ado — types

Read by `ticket-fetch`. Maps this source's own vocabulary onto one of the canonical types in `ticket-types/`. **It is a mapping and nothing else** — what a type then means is the type file's business, never this file's.

## Tags are consulted first

Neither Spike nor Tech Debt is a native work item type here, so a tag is the only way anyone can say a work item is one. A matching tag therefore **overrides** the work item type rather than merely supplementing it.

`System.Tags` is a single semicolon-separated string. Compare case-insensitively, trimmed.

| Tag | Canonical type |
| --- | --- |
| `spike`, `research`, `investigation` | `spike` |
| `tech-debt`, `techdebt`, `tech debt`, `technical debt`, `refactor` | `tech-debt` |

## Then the work item type

`System.WorkItemType`, compared case-insensitively.

| `System.WorkItemType` | Canonical type |
| --- | --- |
| User Story, Product Backlog Item, Feature, Epic, Requirement | `user-story` |
| Bug, Defect | `bug` |
| Task, Issue | `task` |

## When nothing matches

Fall back to `task`, and **say so in one line** — never silently. The value that did not map is kept verbatim in `ticket.json` as `native_type`, so nothing is lost by the fallback.

## Override

`--type {type}` on any driver wins over everything above. It is recorded in `ticket.json` alongside the untouched `native_type`, so the next skill inherits it with no flag.
