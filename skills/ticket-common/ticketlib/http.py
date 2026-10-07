#!/usr/bin/env python3
"""
The bearer-token HTTP calls a remote provider needs.

A provider that authenticates some other way (a CLI, a local file) does not
import this at all.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

from .errors import EXIT_ERROR, TicketError

# Caught so one bad relation does not abort a whole tree.
NETWORK_ERRORS = (urllib.error.URLError, json.JSONDecodeError, OSError)


class CredentialExpiredError(TicketError):
    """
    A cached credential can expire mid-run. Aborting beats continuing: every
    later call fails the same way and leaves a partial snapshot that reads as
    complete.
    """

    def __init__(self, message: str):
        super().__init__(message, EXIT_ERROR)


def raise_if_unauthorized(exc: urllib.error.HTTPError, hint: str) -> None:
    if exc.code == 401:
        raise CredentialExpiredError(
            f"The server rejected the credential (HTTP 401). {hint}"
        ) from exc


def get_json(url: str, auth_header: str, hint: str = "") -> dict:
    request = urllib.request.Request(url, headers={"Authorization": auth_header})
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        # HTTPError is a URLError: without this, NETWORK_ERRORS swallows the 401.
        raise_if_unauthorized(exc, hint)
        raise


def post_json(url: str, auth_header: str, payload: dict, hint: str = "") -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise_if_unauthorized(exc, hint)
        body = exc.read().decode(errors="replace")
        raise TicketError(f"HTTP {exc.code} — {exc.reason}\n{body}") from exc


def download(url: str, auth_header: str, dest: Path, hint: str = "") -> tuple[bool, str]:
    """Returns (succeeded, error_message). A 401 raises rather than returning."""
    request = urllib.request.Request(url, headers={"Authorization": auth_header})
    try:
        with urllib.request.urlopen(request) as response:
            dest.write_bytes(response.read())
        return True, ""
    except urllib.error.HTTPError as exc:
        raise_if_unauthorized(exc, hint)
        return False, str(exc)
    except (urllib.error.URLError, OSError) as exc:
        return False, str(exc)
