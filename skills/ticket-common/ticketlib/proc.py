#!/usr/bin/env python3
"""Running an external command, with the Windows quirks handled once."""

import shutil
import subprocess


def which(name: str) -> str | None:
    # On Windows `az` and `gh` are .cmd shims, which CreateProcess will not
    # find from the bare name the way PATHEXT does.
    return shutil.which(name)


def run(
    command: list[str],
    cwd: str | None = None,
    timeout: int = 60,
    stdin_text: str | None = None,
) -> tuple[int, str, str]:
    """Returns (returncode, stdout, stderr). A missing executable is -1."""
    executable = which(command[0])
    if not executable:
        return -1, "", f"'{command[0]}' not found on PATH."

    try:
        result = subprocess.run(
            [executable, *command[1:]],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin_text,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return -1, "", f"'{command[0]}' timed out after {timeout}s."
    except OSError as exc:
        return -1, "", f"could not run '{command[0]}' — {exc}"

    return result.returncode, result.stdout, result.stderr
