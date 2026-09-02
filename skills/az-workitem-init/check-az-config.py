#!/usr/bin/env python3
"""
Checks whether ~/.az-workitems/config.json exists for the current user.
Prints config contents with PAT masked, or "not_found" if the file is absent.
Exit code: 0 if found, 1 if not found.
"""

import json
import sys
from pathlib import Path


def mask_pat(pat: str) -> str:
    if len(pat) <= 3:
        return "*" * len(pat)
    return pat[:3] + "*" * (len(pat) - 3)


def main() -> int:
    # Path.home() resolves to %USERPROFILE% on Windows and $HOME on Linux/macOS.
    config_path = Path.home() / ".az-workitems" / "config.json"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("not_found")
        return 1
    except (json.JSONDecodeError, OSError) as exc:
        print(f"not_found (unreadable: {exc})")
        return 1

    masked = dict(config)
    if "pat" in masked:
        masked["pat"] = mask_pat(masked["pat"])

    print(json.dumps(masked, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
