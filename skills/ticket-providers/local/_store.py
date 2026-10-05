#!/usr/bin/env python3
"""
Reading and writing `raw/ticket.md`, the local store's source of truth.

Its frontmatter is the suite's tiny subset, parsed by `ticketlib.frontmatter`.
"""

import hashlib
import re
from pathlib import Path

from ticketlib.frontmatter import FENCE as FRONTMATTER_FENCE
from ticketlib.frontmatter import parse as parse_frontmatter
from ticketlib.frontmatter import render as render_frontmatter

# The sections that carry meaning. Anything else a user writes is carried
# through with its heading as a label rather than being silently dropped.
KNOWN_SECTIONS = ("Description", "Acceptance Criteria", "Comments", "Links")

SECTION_PATTERN = re.compile(r"^## +(.+?) *$", re.MULTILINE)


def parse_sections(body: str) -> list[dict]:
    """Every `## ` section in order, each flagged as known or carried through."""
    matches = list(SECTION_PATTERN.finditer(body))
    sections: list[dict] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        heading = match.group(1).strip()
        sections.append(
            {
                "heading": heading,
                "known": heading in KNOWN_SECTIONS,
                "content": body[start:end].strip(),
            }
        )

    return sections


def read(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    return {
        "frontmatter": frontmatter,
        "sections": parse_sections(body),
        "body": body,
        "text": text,
    }


def section_content(parsed: dict, heading: str) -> str:
    for section in parsed["sections"]:
        if section["heading"] == heading:
            return section["content"]
    return ""


def set_frontmatter(path: Path, key: str, value: str, dry_run: bool = False) -> None:
    """
    Set one frontmatter key in place, leaving every other line byte-for-byte as it was.

    Re-rendering the whole block would reorder keys and drop any comment a
    person wrote there; this file is hand-edited, so only the one line moves.
    Line endings are read and written untranslated for the same reason.

    `dry_run` raises exactly what a real run would and writes nothing, so a
    caller can find out before it changes anything else.
    """
    with path.open(encoding="utf-8", newline="") as handle:
        lines = handle.read().splitlines(keepends=True)
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        raise ValueError(f"{path} has no frontmatter block")

    end = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == FRONTMATTER_FENCE
        ),
        None,
    )
    if end is None:
        raise ValueError(f"{path} has an unterminated frontmatter block")

    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    entry = f"{key}: {value}{newline}"
    for index in range(1, end):
        if lines[index].partition(":")[0].strip() == key:
            lines[index] = entry
            break
    else:
        lines.insert(end, entry)

    if dry_run:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("".join(lines))


def fingerprint(path: Path) -> str:
    """
    A content hash, which is the whole of this store's drift signal.

    There is no upstream revision counter to compare against, so the file's own
    content is the only thing that can say whether it moved.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def replace_section(path: Path, heading: str, content: str) -> bool:
    """
    Overwrite one `##` section's content wholesale; every other section is left
    byte-for-byte as it was. Returns whether `heading` was found at all — the
    caller decides what a miss means, since this module never raises for it.
    """
    text = path.read_text(encoding="utf-8")
    content = content.strip() + "\n"

    matches = list(SECTION_PATTERN.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip() != heading:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        head, tail = text[:start].rstrip("\n"), text[end:]
        path.write_text(f"{head}\n\n{content}\n{tail}", encoding="utf-8")
        return True

    return False


SKELETON = """{frontmatter}

# {title}

## Description

{description}

## Acceptance Criteria

{acceptance}

## Comments

## Links
"""


def render_skeleton(
    frontmatter: dict, title: str, description: str, acceptance: str
) -> str:
    return SKELETON.format(
        frontmatter=render_frontmatter(frontmatter),
        title=title,
        description=description,
        acceptance=acceptance,
    )
