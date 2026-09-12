# github — types

Read by `ticket-fetch`. Maps this source's own vocabulary onto one of the canonical types in `ticket-types/`. **It is a mapping and nothing else** — what a type then means is the type file's business, never this file's.

## Labels are the only signal

**This source has no type field.** An issue is an issue; a label is the only way anyone can say what kind of work it is. So unlike a source with a native type, there is nothing here for a label to override — the label *is* the whole signal.

Labels are compared case-insensitively and trimmed, in the order the issue lists them. The first that maps wins.

| Label | Canonical type |
| --- | --- |
| `bug`, `defect` | `bug` |
| `spike`, `research`, `investigation` | `spike` |
| `tech-debt`, `techdebt`, `tech debt`, `technical debt`, `refactor` | `tech-debt` |
| `enhancement`, `feature`, `story` | `user-story` |

`bug` and `enhancement` are both in the default label set, so those two map correctly even on a repository nobody has configured.

## When nothing matches

Fall back to `task`, and **say so in one line** — never silently. Mention that this source has no type field, so an unlabelled issue is genuinely untyped rather than mislabelled: `--type` is the fix, not a repository setting.

The full label list is kept verbatim in `ticket.json` as `native_type`, so nothing is lost by the fallback.

## Override

`--type {type}` on any driver wins over everything above. It is recorded in `ticket.json` alongside `native_type`, so the next skill inherits it with no flag. Expect it to be used more often here than elsewhere, precisely because labels are optional.
