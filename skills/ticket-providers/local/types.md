# local — types

Read by `ticket-new`. Maps this source's own vocabulary onto one of the canonical types in `ticket-types/`. **It is a mapping and nothing else** — what a type then means is the type file's business, never this file's.

## The frontmatter key, directly

```
type: tech-debt
```

The frontmatter `type` key holds a canonical type name verbatim. There is no native vocabulary to translate, because this store was designed after the type set existed — the author writes the canonical name and it is used as-is.

Compare case-insensitively and trimmed.

## When it is absent or unrecognised

Fall back to `task`, and **say so in one line** — never silently. The value that did not map is kept verbatim in `ticket.json` as `native_type`, so a typo is visible rather than lost.

## Override

`--type {type}` on any driver wins over the frontmatter. It is recorded in `ticket.json` alongside `native_type`, so the next skill inherits it with no flag — and the frontmatter still says what the author originally wrote.
