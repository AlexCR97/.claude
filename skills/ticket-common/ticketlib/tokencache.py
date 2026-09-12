#!/usr/bin/env python3
"""
Caching a bearer token in a source's config.json.

Nothing here is specific to any one source: a provider that authenticates with
a bearer token stores the issuer's whole response under `token` and reuses it
until it nears expiry. The dual `expires_on`/`expiresOn` handling and the
fail-closed refresh margin are the parts worth not re-deriving per source.
"""

from datetime import datetime, timezone

# Refreshing early costs one cheap call; a 401 mid-fetch costs a partial run.
REFRESH_MARGIN_SECONDS = 300


def make_auth_header(token: dict) -> str:
    return f"{token.get('tokenType') or 'Bearer'} {token['accessToken']}"


def expires_at(token: dict) -> float | None:
    """The expiry as a UTC epoch timestamp; None when unreadable."""
    # expires_on is an unambiguous epoch; expiresOn's older form has no offset.
    epoch = token.get("expires_on")
    if isinstance(epoch, (int, float)):
        return float(epoch)
    if isinstance(epoch, str) and epoch.strip().lstrip("-").isdigit():
        return float(epoch.strip())

    raw = token.get("expiresOn")
    if not isinstance(raw, str) or not raw.strip():
        return None

    try:
        parsed = datetime.fromisoformat(raw.strip().replace(" ", "T"))
    except ValueError:
        return None

    # The older "2026-09-03 17:48:31.000000" form is local time with no offset.
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()

    return parsed.timestamp()


def local_expiry_text(token: dict) -> str:
    """Local wall-clock expiry; empty when unknown."""
    expiry = expires_at(token)
    if expiry is None:
        return ""

    local = datetime.fromtimestamp(expiry, tz=timezone.utc).astimezone()
    return f"{local:%Y-%m-%d %H:%M:%S}"


def is_usable(token: object) -> bool:
    if not isinstance(token, dict) or not token.get("accessToken"):
        return False

    expiry = expires_at(token)
    if expiry is None:
        # Fail closed: a fresh token is cheap, a 401 mid-run is not.
        return False

    return expiry > datetime.now(timezone.utc).timestamp() + REFRESH_MARGIN_SECONDS


def describe(token: object) -> str:
    """Summarize a cached token without ever revealing it."""
    if not isinstance(token, dict) or not token.get("accessToken"):
        return "absent — a credential is acquired on the next call"

    expiry_text = local_expiry_text(token)
    if not expiry_text:
        return "expiry unknown — refreshed on the next call"

    state = "valid" if is_usable(token) else "expired, refreshed on next call"
    return f"{state} (expires {expiry_text})"
