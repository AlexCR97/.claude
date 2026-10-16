#!/usr/bin/env python3
"""
Azure DevOps REST calls, made through `az rest`.

`az` owns the credential: it signs the request and refreshes the token itself,
so nothing here ever sees, stores or passes one. Every response is written to a
file and read back as UTF-8, because the console codepage `az` prints in on
Windows would turn any non-ASCII character in a ticket into mojibake.
"""

import json
import tempfile
from pathlib import Path

from . import proc
from .errors import EXIT_ERROR, TicketError

# The audience a token must be issued for to be accepted by dev.azure.com.
RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"

API_VERSION = "7.1"

AZ_LOGIN_HINT = (
    f"Sign in with `az login --scope {RESOURCE}/.default`, then re-run this skill."
)

# What `az` prints when the sign-in, rather than the request, is what failed.
_SIGN_IN_MARKERS = ("AADSTS", "az login", "Unauthorized")


class AzRestError(OSError):
    """One request failed for a reason that says nothing about the rest, such as a 404."""


def _fail(detail: str) -> Exception:
    if any(marker in detail for marker in _SIGN_IN_MARKERS):
        # Aborting beats continuing: every later call would fail the same way and
        # leave a partial snapshot that reads as complete.
        return TicketError(
            f"Azure DevOps rejected the sign-in — {detail.strip()}",
            EXIT_ERROR,
            AZ_LOGIN_HINT,
        )
    return AzRestError(detail.strip())


def _run(
    method: str,
    url: str,
    params: list[str],
    output: Path,
    extra: list[str],
    api_version: str = API_VERSION,
) -> None:
    command = [
        "az",
        "rest",
        "--resource",
        RESOURCE,
        "--method",
        method,
        "--url",
        url,
        "--output-file",
        str(output),
        *extra,
    ]
    # Parameters travel as their own arguments: `&` inside a URL would be read
    # as a command separator by the cmd.exe that runs the `az` shim on Windows.
    command += ["--url-parameters", *params, f"api-version={api_version}"]
    code, _, stderr = proc.run(command, timeout=120)
    if code != 0:
        raise _fail(stderr or f"az exited with code {code}")


def get_json(
    url: str, params: list[str] | None = None, api_version: str = API_VERSION
) -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        output = Path(scratch) / "response.json"
        _run("get", url, params or [], output, [], api_version)
        try:
            return json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AzRestError(f"{url} returned output that is not JSON — {exc}") from exc


def send_json(
    method: str,
    url: str,
    body: object,
    content_type: str = "application/json",
) -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        payload = Path(scratch) / "body.json"
        payload.write_text(json.dumps(body), encoding="utf-8")
        output = Path(scratch) / "response.json"
        _run(
            method.lower(),
            url,
            [],
            output,
            ["--body", f"@{payload}", "--headers", f"Content-Type={content_type}"],
        )
        try:
            return json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AzRestError(f"{url} returned output that is not JSON — {exc}") from exc


def download(url: str, dest: Path) -> tuple[bool, str]:
    """
    Returns (succeeded, error_message). A sign-in failure raises rather than returning.

    The query is dropped: an attachment is addressed by its id alone, and
    `fileName` only names the download.
    """
    try:
        _run("get", url.partition("?")[0], [], dest, [])
    except AzRestError as exc:
        dest.unlink(missing_ok=True)
        return False, str(exc)
    return True, ""
