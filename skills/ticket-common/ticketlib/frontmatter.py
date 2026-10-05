#!/usr/bin/env python3
"""
The frontmatter subset every markdown file in the suite is read with.

Deliberately tiny — flat `key: value` pairs plus `[a, b]` lists — so it parses
in about thirty lines of stdlib and needs no YAML dependency. That is the same
rule that chose JSON for provider.json: a file format nobody can read without
installing something is a file format that stops working.
"""

FENCE = "---"


def parse(text: str) -> tuple[dict, str]:
    """Returns (frontmatter, body). Absent frontmatter reads as empty."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FENCE:
        return {}, text

    try:
        end = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == FENCE
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


def render(data: dict) -> str:
    lines = [FENCE]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(item) for item in value)}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append(FENCE)
    return "\n".join(lines)
