#!/usr/bin/env python3
"""
Whether a script artifact may run without asking.

Every script a skill writes opens with a header declaring `effect: read-only`
or `effect: writes`, and optionally `cost: heavy`. A declaration is a claim,
so it is checked against the code before it is trusted: a script runs unasked
only when its header says read-only *and* nothing in it contradicts that. A
header that is absent, unreadable or disagreeing with the code falls back to
asking, as does `cost: heavy` and any target the config marks `sensitive`.

The check is deliberately conservative and textual. It can be fooled by a
script built to fool it, but it cannot be fooled by a careless header, which
is the failure it exists to catch.
"""

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

# A header is read from the first lines only, so a stray comment deep in the file is not one.
HEADER_LINES = 15

COMMENT_PREFIX = re.compile(r"^\s*(?:#|--|//|;|REM\b|/\*|\*)\s?", re.IGNORECASE)
EFFECT_PATTERN = re.compile(r"\beffect\s*:\s*(read-only|writes)\b", re.IGNORECASE)
COST_PATTERN = re.compile(r"\bcost\s*:\s*(heavy)\b", re.IGNORECASE)

# What a script does that changes something. Each entry is a reason shown to the developer.
WRITE_INDICATORS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("opens a file for writing", re.compile(r"""\bopen\([^)]*,\s*['"][^'"]*[wax+][^'"]*['"]""")),
    ("writes a file", re.compile(r"\.(?:write_text|write_bytes|write|writelines|dump|to_csv|to_json|save|savefig)\(")),
    ("changes the filesystem", re.compile(r"\b(?:os\.(?:remove|unlink|rename|replace|rmdir|makedirs|mkdir|chmod)|shutil\.\w+|Path\([^)]*\)\.(?:mkdir|unlink|rmdir|rename|touch)|Remove-Item|New-Item|Set-Content|Out-File|Add-Content|Move-Item|Copy-Item|File\.Write\w*|File\.Delete|Directory\.Create\w*)")),
    ("redirects output into a file", re.compile(r"(?:^|[^<>=|&\-\d])\s*\d?>>?\s*(?!&|/dev/null|\$null|NUL\b)[\w./$~\"'{-]", re.MULTILINE)),
    ("runs a shell command that writes", re.compile(r"\b(?:rm|mv|cp|mkdir|rmdir|touch|chmod|chown|tee|dd|truncate|sed\s+-i)\s")),
    ("starts another process", re.compile(r"\b(?:subprocess\.\w+|os\.system|os\.popen|Popen|Start-Process|Invoke-Expression|\biex\b|exec\(|eval\()")),
    ("calls a mutating HTTP method", re.compile(r"""(?:\b(?:requests|httpx|session|client)\.(?:post|put|patch|delete)\(|method\s*=\s*['"](?:POST|PUT|PATCH|DELETE)['"]|curl\b[^\n]*(?:-X\s*(?:POST|PUT|PATCH|DELETE)|--data|-d\s)|Invoke-(?:RestMethod|WebRequest)\b[^\n]*-Method\s+(?:Post|Put|Patch|Delete)|-X\s*(?:POST|PUT|PATCH|DELETE))""", re.IGNORECASE)),
    ("mutates a database", re.compile(r"\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+(?:TABLE|DATABASE|INDEX|VIEW)|ALTER\s+(?:TABLE|DATABASE)|CREATE\s+(?:TABLE|DATABASE|INDEX|VIEW)|TRUNCATE\s+TABLE|MERGE\s+INTO|EXEC(?:UTE)?\s+\w+)\b", re.IGNORECASE)),
    ("installs something", re.compile(r"\b(?:pip3?\s+install|npm\s+(?:install|i)\b|pnpm\s+(?:add|install)|yarn\s+add|dotnet\s+(?:add|tool\s+install|restore)|apt(?:-get)?\s+install|brew\s+install|choco\s+install|winget\s+install|Install-Module|cargo\s+install|go\s+install|gem\s+install)", re.IGNORECASE)),
    ("changes git state", re.compile(r"\bgit\s+(?:add|commit|push|pull|checkout|switch|reset|rebase|merge|stash|clean|restore|tag|branch\s+-[dDmM]|worktree\s+(?:add|remove|prune)|config\s+(?!--get|--list|-l)|fetch|clone|cherry-pick|revert)\b")),
    ("changes a GitHub resource", re.compile(r"\bgh\s+(?:issue\s+(?:create|edit|close|comment|delete)|pr\s+(?:create|edit|merge|close|comment)|api\s+(?:[^\n]*(?:-X|--method)\s*(?:POST|PUT|PATCH|DELETE))|release\s+(?:create|delete)|repo\s+(?:create|delete|edit))", re.IGNORECASE)),
    ("changes an Azure resource", re.compile(r"\baz\s+(?:\S+\s+)*(?:create|update|delete|set|add|remove|start|stop|restart|invoke)\b")),
)


@dataclass
class Verdict:
    run_without_asking: bool
    declared_effect: str | None
    cost: str | None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "run_without_asking": self.run_without_asking,
            "declared_effect": self.declared_effect,
            "cost": self.cost,
            "reasons": self.reasons,
        }


def header_of(text: str) -> tuple[str | None, str | None]:
    """The declared (effect, cost) from the first comment lines, lowercased; None where absent."""
    effect: str | None = None
    cost: str | None = None
    for line in text.splitlines()[:HEADER_LINES]:
        if not COMMENT_PREFIX.match(line):
            continue
        if effect is None and (found := EFFECT_PATTERN.search(line)):
            effect = found.group(1).lower()
        if cost is None and (found := COST_PATTERN.search(line)):
            cost = found.group(1).lower()
    return effect, cost


def without_header_and_comments(text: str) -> str:
    """The code alone: a comment saying 'we never DELETE FROM here' is not a write."""
    kept = []
    for line in text.splitlines():
        if COMMENT_PREFIX.match(line) and not line.lstrip().startswith("#!"):
            continue
        kept.append(line)
    return "\n".join(kept)


def write_indicators(code: str) -> list[str]:
    return [reason for reason, pattern in WRITE_INDICATORS if pattern.search(code)]


def sensitive_hits(text: str, patterns: list[str]) -> list[str]:
    lowered = text.lower()
    hits = []
    for pattern in patterns:
        needle = pattern.lower()
        if "*" in needle or "?" in needle:
            if any(fnmatch.fnmatchcase(token, needle) for token in re.split(r"[\s'\"`()<>,;]+", lowered)):
                hits.append(pattern)
        elif needle in lowered:
            hits.append(pattern)
    return hits


def check(path: Path, sensitive: list[str]) -> Verdict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Verdict(False, None, None, [f"{path.name} cannot be read as text, so its header cannot be verified"])

    effect, cost = header_of(text)
    reasons: list[str] = []

    if effect is None:
        reasons.append("the header declares no `effect:`")
    elif effect == "writes":
        reasons.append("the header declares `effect: writes`")
    else:
        indicators = write_indicators(without_header_and_comments(text))
        if indicators:
            reasons.append(
                "the header says read-only but the code " + "; ".join(indicators)
            )

    if cost == "heavy":
        reasons.append("the header declares `cost: heavy`")

    hits = sensitive_hits(text, sensitive)
    if hits:
        reasons.append("it targets a sensitive pattern: " + ", ".join(hits))

    return Verdict(not reasons, effect, cost, reasons)
