"""
Connection profiles: flat `.env` files in the connections home, one per profile.

A profile holds a connection's credentials and a few reserved `CONNECTION_*`
keys describing it. Nothing here ever prints a value: reports carry profile and
key names only, because the agent reading them must never see a secret.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

KIND_KEY = "CONNECTION_KIND"
ENV_FILE_KEY = "CONNECTION_ENV_FILE"
RESERVED_PREFIX = "CONNECTION_"

# A shorter value would mangle ordinary output wherever it happens to appear,
# so it is never masked and `check` warns about it instead.
MASK_MIN_LENGTH = 4

REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

PRODUCTION_KEY = "CONNECTION_PRODUCTION"
PRODUCTION_SEGMENTS = frozenset({"prod", "production"})
NON_PRODUCTION_SEGMENTS = frozenset(
    {
        "dev",
        "development",
        "int",
        "integration",
        "qa",
        "test",
        "uat",
        "stage",
        "staging",
        "sandbox",
        "local",
        "localhost",
        "preprod",
        "pre",
    }
)
NAME_SEPARATORS = re.compile(r"[-_.]")
FLAGS = {"true": True, "false": False}


@dataclass
class ParsedEnv:
    values: dict[str, str] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


def parse_env(text: str) -> ParsedEnv:
    parsed = ParsedEnv()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            parsed.problems.append(f"line {number} is not a KEY=VALUE assignment")
            continue
        parsed.values[key] = expand(key, unquote(value.strip()), parsed)
    return parsed


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def expand(key: str, value: str, parsed: ParsedEnv) -> str:
    """A reference takes an earlier key of the same file first, then the process environment."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in parsed.values:
            return parsed.values[name]
        if name in os.environ:
            return os.environ[name]
        parsed.problems.append(f"{key} references ${{{name}}}, which is not defined")
        return match.group(0)

    return REFERENCE.sub(replace, value)


def load_profile(file: Path) -> ParsedEnv:
    """The profile's own keys, then those of the env file it names, the profile's winning."""
    parsed = parse_env(file.read_text(encoding="utf-8"))
    reference = parsed.values.get(ENV_FILE_KEY)
    if not reference:
        return parsed
    target = file.parent / Path(reference).expanduser()
    if not target.is_file():
        parsed.problems.append(f"{ENV_FILE_KEY} names {reference}, which is not a file")
        return parsed
    referenced = parse_env(target.read_text(encoding="utf-8"))
    parsed.problems.extend(
        f"{target.name}: {problem}" for problem in referenced.problems
    )
    for key, value in referenced.values.items():
        parsed.values.setdefault(key, value)
    return parsed


def profile_files() -> list[Path]:
    home = paths.connections_home()
    return sorted(home.glob("*.env")) if home.is_dir() else []


def classify_by_name(profile: str) -> bool | None:
    """
    Whether a profile name says production: True, False, or None when it says nothing.

    A production segment wins even beside a non-production one (`dev-prod-mirror`),
    except `pre` directly followed by `prod`, which is the one term `pre-prod`.
    """
    segments = [part for part in NAME_SEPARATORS.split(profile.casefold()) if part]
    production = False
    recognised = False
    index = 0
    while index < len(segments):
        segment = segments[index]
        if segment == "pre" and segments[index + 1 : index + 2] == ["prod"]:
            recognised = True
            index += 2
            continue
        if segment in PRODUCTION_SEGMENTS:
            production = True
        elif segment in NON_PRODUCTION_SEGMENTS:
            recognised = True
        index += 1
    if production:
        return True
    return False if recognised else None


def production_mark(profile: str, values: Mapping[str, str]) -> tuple[bool, str]:
    """The mark and what decided it. Anything unreadable or unrecognised is production."""
    flag = values.get(PRODUCTION_KEY)
    if flag is not None:
        return FLAGS.get(flag.strip().casefold(), True), "profile"
    by_name = classify_by_name(profile)
    if by_name is not None:
        return by_name, "name"
    return True, "default"


def list_connections() -> Mapping[str, object]:
    entries = []
    for file in profile_files():
        values = load_profile(file).values
        production, source = production_mark(file.stem, values)
        entries.append(
            {
                "profile": file.stem,
                "kind": values.get(KIND_KEY),
                "production": production,
                "production_source": source,
            }
        )
    return {"home": str(paths.connections_home()), "connections": entries}


def check_profile(file: Path) -> dict[str, object]:
    parsed = load_profile(file)
    problems = list(parsed.problems)
    if KIND_KEY not in parsed.values:
        problems.append(f"{KIND_KEY} is missing")
    flag = parsed.values.get(PRODUCTION_KEY)
    if flag is not None and flag.strip().casefold() not in FLAGS:
        problems.append(f"{PRODUCTION_KEY} must be true or false")
    warnings = [
        f"{key} is shorter than {MASK_MIN_LENGTH} characters, so it will not be masked"
        for key, value in parsed.values.items()
        if not key.startswith(RESERVED_PREFIX) and 0 < len(value) < MASK_MIN_LENGTH
    ]
    return {
        "profile": file.stem,
        "ok": not problems,
        "problems": problems,
        "warnings": warnings,
        "keys": list(parsed.values),
    }


def check_connections() -> dict[str, object]:
    reports = [check_profile(file) for file in profile_files()]
    return {
        "ok": all(report["ok"] for report in reports),
        "profiles": reports,
    }
