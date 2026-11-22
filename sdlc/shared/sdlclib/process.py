"""
Run a command line tool with a time limit, turning a hang into an `SdlcError`.

`gh`, `az` and `git` can stall on a network or credential prompt; without this a
skill would see a raw traceback instead of an error it can report.
"""

import os
import subprocess
from pathlib import Path

from .errors import SdlcError

DEFAULT_TIMEOUT_SECONDS = 120

# Read per call, not at import, so a slow connection can lengthen the limit without a code change.
TIMEOUT_VARIABLE = "SDLC_CLI_TIMEOUT"


def timeout_seconds() -> float:
    try:
        return float(os.environ[TIMEOUT_VARIABLE])
    except (KeyError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def run(
    command: list[str], *, cwd: Path | None = None, text: bool = False
) -> subprocess.CompletedProcess:
    limit = timeout_seconds()
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            timeout=limit,
            check=False,
            text=text,
            encoding="utf-8" if text else None,
        )
    except subprocess.TimeoutExpired as error:
        tool = Path(command[0]).stem
        raise SdlcError(
            f"`{tool}` did not answer within {limit:g} seconds",
            hint=f"`{tool}` is probably waiting on a sign-in or the network; "
            f"fix that and try again, or raise {TIMEOUT_VARIABLE}.",
        ) from error
