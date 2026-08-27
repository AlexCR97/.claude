---
name: unwrap-markdown
description: Join soft-wrapped Markdown prose so each paragraph, list item and blockquote sits on one physical line. Removes only line breaks — never a word, never a character of content. Use on requests like "one paragraph per line", "unwrap this markdown", "remove the hard wrapping", "stop wrapping at 80 columns", "reflow these paragraphs".
allowed-tools: Read Grep Glob Edit Write Bash(git diff:*) Bash(git status:*) Bash(git show:*) Bash(cat:*) Bash(cp:*) Bash(tr:*) Bash(diff:*) Bash(python:*) Bash(node:*)
argument-hint: "[file <path>|dir <path>|changes|all]"
---

# Unwrap Markdown

Turn wrapped prose into one line per block. A paragraph split across six lines becomes one line; the rendered output is byte-identical.

## The Premise

Soft wrapping is an editor artifact, not content. Markdown collapses a single newline into a space, so where a paragraph breaks says nothing about what it means.

It costs, though. A one-word edit reflows the whole paragraph and the diff shows six changed lines instead of one. Two people with different column limits fight over every file. Grep for a phrase and miss it because it straddles a break.

One line per block removes all three. The renderer sees the same document.

This skill deletes line breaks. It never adds, removes, rewrites or reorders a word.

---

## Supported Scopes

`$ARGUMENTS` determines what to unwrap:

- `file <path>` — one Markdown file.
- `dir <path>` — every `*.md` / `*.mdx` file under a directory, recursively.
- `changes` — Markdown files in the current git diff (staged + unstaged).
- `all` — every Markdown file under the working directory.

If `$ARGUMENTS` is empty, null, or unrecognized, ask which file or directory to unwrap. Do not guess.

For `changes`, unwrap the whole file, not only the changed hunks — a half-unwrapped file is worse than either state.

---

## Step 1 — Join These

Within one block, replace each newline and the following line's leading indentation with a single space.

- **Paragraphs.** Every consecutive run of non-blank prose lines becomes one line.
- **List items.** Continuation lines fold into the item they belong to. Each item keeps its own line, its own marker, and its indentation. A nested list stays nested.
- **Blockquotes.** Lines inside a `>` block fold into one line carrying a single `>` marker. Lazy continuation lines — wrapped lines with no `>` of their own — fold in too.

Blocks are bounded by blank lines. Never join across one.

### Joining rules

- Exactly one space at each join. Collapse the continuation line's leading whitespace into it.
- Strip trailing whitespace from joined lines, except where it forms a hard break (below).
- Keep the block's own leading indentation — the first line's.
- Keep blank lines exactly as they are, including the blank lines of a loose list.
- Preserve the file's line endings, BOM, and final newline.

---

## Step 2 — Never Touch These

Joining any of these changes what renders. Copy them through untouched, line breaks included.

- **Fenced code blocks** — ``` or `~~~`, any info string, any fence length. Match the closing fence to the opening one; a longer fence can nest a shorter one.
- **Indented code blocks** — four spaces or a tab, where the context makes it code rather than a list continuation.
- **Front matter** — YAML or TOML at the top of the file.
- **Tables** — every pipe row and the delimiter row.
- **HTML blocks** and JSX/MDX expressions.
- **Hard line breaks** — a line ending in two or more spaces, or in a backslash. The break is deliberate. Keep the line break and the trailing marker.
- **Setext headings** — a line followed by `===` or `---`. Joining the line above destroys the heading.
- **Thematic breaks** (`---`, `***`, `___`), ATX headings, and any line that already stands alone.
- **Link reference definitions**, footnote definitions, and abbreviation definitions.
- **Math blocks** (`$$`) and directive/admonition fences (`:::`).

> When a line is ambiguous — an indented block that could be code or could be a list continuation — leave it alone and note it in the report.

---

## Step 3 — Apply

- Files under ~200 lines: edit directly.
- Anything larger, or `dir` / `all` scope: write a script to `{scratchpad}/unwrap.py`, run it over the files, then delete it. Deterministic beats retyped.

Never retype prose. Every character of content must survive by being copied, not rewritten — retyping is how a paragraph silently loses a word.

**The operation is idempotent.** Running it twice must produce no second change. An already-unwrapped file is reported as clean, not rewritten.

---

## Step 4 — Verify

Content changed only if whitespace changed. Prove it: collapse every whitespace run in both versions to a single space and diff.

    cp doc.md "$SCRATCH/doc.before.md"      # before editing
    tr -s '[:space:]' ' ' < "$SCRATCH/doc.before.md" > "$SCRATCH/a.txt"
    tr -s '[:space:]' ' ' < doc.md > "$SCRATCH/b.txt"
    diff "$SCRATCH/a.txt" "$SCRATCH/b.txt"

Empty diff means no word was added, dropped or altered. Anything else is a bug in the edit — revert the file and redo it.

This check does not cover *structure*. Also confirm by eye that code fences, tables and hard breaks came through intact.

---

## Step 5 — Report

Output this and nothing more:

    ## Unwrapped — {scope}

    | File | Blocks joined | Lines before → after |
    | ---- | ------------- | -------------------- |

    **Preserved:** {n} code blocks, {n} tables, {n} hard breaks, {n} front matter
    **Skipped:** {file} — {why}

    Whitespace-only change verified.

    Review with: `git diff --ignore-all-space` (expect: no output)

- **Blocks joined** counts paragraphs, list items and blockquotes that lost at least one break.
- Omit the *Skipped* line when nothing was skipped.
- Files already unwrapped get one line saying so, not a table row.
- No preamble, no closing summary.
