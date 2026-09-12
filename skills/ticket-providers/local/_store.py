#!/usr/bin/env python3
"""
Reading and writing `raw/ticket.md`, the local store's source of truth.

The frontmatter subset is deliberately tiny — flat `key: value` pairs plus
`[a, b]` lists — so it parses in about thirty lines of stdlib and needs no YAML
dependency. That is the same rule that chose JSON for provider.json: a store
format nobody can read without installing something is a store format that
stops working.
"""

import hashlib
import re
from pathlib import Path

FRONTMATTER_FENCE = "---"

# The sections that carry meaning. Anything else a user writes is carried
# through with its heading as a label rather than being silently dropped.
KNOWN_SECTIONS = ("Description", "Acceptance Criteria", "Comments", "Links")

SECTION_PATTERN = re.compile(r"^## +(.+?) *$", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Returns (frontmatter, body). Absent frontmatter reads as empty."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return {}, text

    try:
        end = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == FRONTMATTER_FENCE
        )
    except StopIteration:
        return {}, text

    data: dict = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key.strip()] = [
                item.strip().strip("\"'")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            data[key.strip()] = value.strip("\"'")

    return data, "\n".join(lines[end + 1 :]).lstrip("\n")


def render_frontmatter(data: dict) -> str:
    lines = [FRONTMATTER_FENCE]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(item) for item in value)}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append(FRONTMATTER_FENCE)
    return "\n".join(lines)


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


def append_comment(path: Path, block: str) -> None:
    """
    Add a block under `## Comments`, creating the section when it is absent.

    Appending rather than rewriting is deliberate: everything else in the file
    was written by a person, and a publish must not reflow their prose.
    """
    text = path.read_text(encoding="utf-8")
    block = block.strip() + "\n"

    matches = list(SECTION_PATTERN.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip() != "Comments":
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        head, tail = text[:end].rstrip("\n"), text[end:]
        path.write_text(f"{head}\n\n{block}\n{tail}", encoding="utf-8")
        return

    path.write_text(
        f"{text.rstrip()}\n\n## Comments\n\n{block}", encoding="utf-8"
    )


SKELETON = """{frontmatter}

# {title}

## Description

{description}

## Acceptance Criteria

{acceptance}

## Comments

## Links
"""


def render_skeleton(frontmatter: dict, title: str, description: str, acceptance: str) -> str:
    return SKELETON.format(
        frontmatter=render_frontmatter(frontmatter),
        title=title,
        description=description,
        acceptance=acceptance,
    )
