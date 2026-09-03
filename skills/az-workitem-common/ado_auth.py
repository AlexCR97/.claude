#!/usr/bin/env python3
"""
Shared Azure DevOps authentication for the az-workitem-* skills.

dev.azure.com accepts an Azure CLI access token as a bearer credential, so the
whole `az account get-access-token` response is cached in config.json and
replaced as it nears expiry.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Config is machine-wide, not per-workspace.
CONFIG_PATH = Path.home() / ".az-workitems" / "config.json"

# Audience an access token must be issued for to be accepted by dev.azure.com.
AZURE_DEVOPS_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"

REFRESH_MARGIN_SECONDS = 300

AZ_LOGIN_HINT = (
    "Sign in with 'az login' so an Azure DevOps token can be acquired, then "
    "re-run this skill."
)


def load_config() -> dict:
    """An absent or unreadable config.json reads as empty."""
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    """Atomic write: a crash cannot leave config.json half-written."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = CONFIG_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    os.replace(temp_path, CONFIG_PATH)


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


def is_usable(token: dict) -> bool:
    if not isinstance(token, dict) or not token.get("accessToken"):
        return False

    expiry = expires_at(token)
    if expiry is None:
        # Fail closed: a fresh token is cheap, a 401 mid-run is not.
        return False

    return expiry > datetime.now(timezone.utc).timestamp() + REFRESH_MARGIN_SECONDS


def fetch_cli_token() -> tuple[dict, str]:
    """Returns (token, error_message); token is empty when acquisition failed."""
    # On Windows 'az' is a .cmd shim, which CreateProcess will not find from
    # the bare name the way PATHEXT does.
    executable = shutil.which("az")
    if not executable:
        return {}, "Azure CLI ('az') not found on PATH."

    command = [
        executable,
        "account",
        "get-access-token",
        "--resource",
        AZURE_DEVOPS_RESOURCE_ID,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {}, "Azure CLI timed out while acquiring an access token."

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        return {}, f"Azure CLI failed to acquire an access token — {detail}"

    try:
        token = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {}, f"Azure CLI returned output that is not JSON — {exc}"

    if not token.get("accessToken"):
        return {}, "Azure CLI response carried no access token."

    return token, ""


def get_token() -> tuple[dict, str]:
    """Returns (token, error_message); token is empty when acquisition failed."""
    config = load_config()
    cached = config.get("token")
    if isinstance(cached, dict) and is_usable(cached):
        return cached, ""

    token, error = fetch_cli_token()
    if error:
        return {}, error

    # Creating a config here would omit the organization and project that
    # /az-workitem-init writes.
    if config:
        config["token"] = token
        save_config(config)

    return token, ""


def require_token() -> dict:
    """Return a usable token or exit(1) with the reason."""
    token, error = get_token()
    if token:
        return token

    print(f"ERROR: {error}", file=sys.stderr)
    print(AZ_LOGIN_HINT, file=sys.stderr)
    raise SystemExit(1)
