#!/usr/bin/env python3
"""
Initializes the .claude/.az-workitems directory and config.json for Azure DevOps work item skills.
"""

import argparse
import base64
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def find_claude_dir(start: Path) -> Path:
    """Return the .claude directory rooted at start, creating it if necessary."""
    claude_dir = start / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    return claude_dir


def mask_pat(pat: str) -> str:
    """Return the first 3 characters followed by asterisks."""
    if len(pat) <= 3:
        return "*" * len(pat)
    return pat[:3] + "*" * (len(pat) - 3)


def validate_credentials(org: str, project: str, pat: str) -> tuple[bool, str]:
    """
    Validate org, project, and PAT against the ADO projects API.
    Returns (success, error_message).
    """
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    url = f"https://dev.azure.com/{org}/_apis/projects/{project}?api-version=7.1"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {encoded}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return True, ""
            return False, f"Unexpected status {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Authentication failed — PAT is invalid or expired."
        if e.code == 404:
            return False, f"Project '{project}' not found in organization '{org}'."
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}"


def prompt_value(name: str, current: str | None = None) -> str:
    """Prompt the user for a value, showing the current one if present."""
    if current:
        prompt = f"{name} [{current}]: "
    else:
        prompt = f"{name}: "

    while True:
        value = input(prompt).strip()
        if value:
            return value
        if current:
            return current
        print(f"  {name} is required.")


def prompt_pat(current_masked: str | None = None) -> str:
    """Prompt the user for a PAT, hiding the current masked value as hint."""
    if current_masked:
        prompt = f"PAT [{current_masked}] (leave blank to keep existing): "
    else:
        prompt = "PAT: "

    while True:
        value = input(prompt).strip()
        if value:
            return value
        if current_masked:
            # User wants to keep the existing PAT — signal this with empty string;
            # caller must substitute the real stored value.
            return ""
        print("  PAT is required.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize .claude/.az-workitems/config.json"
    )
    parser.add_argument("--org", help="Azure DevOps organization name")
    parser.add_argument("--project", help="Azure DevOps project name")
    parser.add_argument("--pat", help="Personal Access Token")
    args = parser.parse_args()

    cwd = Path.cwd()
    claude_dir = find_claude_dir(cwd)
    workitems_dir = claude_dir / ".az-workitems"
    config_path = workitems_dir / "config.json"

    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    # Resolve values: CLI args → existing config → interactive prompt
    org = args.org or existing.get("organization") or None
    project = args.project or existing.get("project") or None
    pat_from_args = args.pat

    interactive = not (args.org and args.project and pat_from_args)

    if interactive:
        print("Enter values (press Enter to keep the current value where shown):")
        print()

    if args.org:
        org = args.org
    else:
        org = prompt_value("Organization", org)

    if args.project:
        project = args.project
    else:
        project = prompt_value("Project", project)

    if pat_from_args:
        pat = pat_from_args
    else:
        current_masked = mask_pat(existing["pat"]) if existing.get("pat") else None
        raw = prompt_pat(current_masked)
        # Empty string means "keep existing"
        pat = raw if raw else existing.get("pat", "")

    if not pat:
        print("ERROR: PAT is required.", file=sys.stderr)
        return 1

    print()
    print("Validating credentials against Azure DevOps...")
    ok, error = validate_credentials(org, project, pat)
    if not ok:
        print(f"ERROR: Validation failed — {error}", file=sys.stderr)
        return 1

    print("Credentials validated successfully.")
    print()

    workitems_dir.mkdir(parents=True, exist_ok=True)
    config = {"organization": org, "project": project, "pat": pat}
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Config written to {config_path.relative_to(cwd)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
