#!/usr/bin/env python3
"""
Checks whether ~/.az-workitems/config.json exists for the current user.
Prints the config with the access token replaced by its status, or
"not_found" if the file is absent.
Exit code: 0 if found, 1 if not found.
"""

import json
import sys
from pathlib import Path

# 'az-workitem-common' is not an importable package name, so add it to sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent / "az-workitem-common"))

from ado_auth import CONFIG_PATH, is_usable, local_expiry_text


def describe_token(token: dict) -> str:
    """Summarize the cached token without ever revealing it."""
    if not isinstance(token, dict) or not token.get("accessToken"):
        return "absent — a token is acquired on the next ADO call"

    expiry_text = local_expiry_text(token)
    if not expiry_text:
        return "expiry unknown — the token is refreshed on the next ADO call"

    state = "valid" if is_usable(token) else "expired, refreshed on next ADO call"
    return f"{state} (expires {expiry_text})"


def main() -> int:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("not_found")
        return 1
    except (json.JSONDecodeError, OSError) as exc:
        print(f"not_found (unreadable: {exc})")
        return 1

    summary = dict(config)
    summary["token"] = describe_token(config.get("token"))

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
