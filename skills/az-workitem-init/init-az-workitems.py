#!/usr/bin/env python3
"""
Initializes the ~/.az-workitems directory and config.json for Azure DevOps work item skills.
"""

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

# 'az-workitem-common' is not an importable package name, so add it to sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent / "az-workitem-common"))

from ado_auth import (
    AZ_LOGIN_HINT,
    CONFIG_PATH,
    fetch_cli_token,
    local_expiry_text,
    make_auth_header,
    save_config,
)

DEFAULT_ORG = "edwire"
DEFAULT_PROJECT = "EW.Educate"


def validate_token(org: str, project: str, token: dict) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    url = f"https://dev.azure.com/{org}/_apis/projects/{project}?api-version=7.1"

    req = urllib.request.Request(url)
    req.add_header("Authorization", make_auth_header(token))
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return True, ""
            return False, f"Unexpected status {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Authentication failed — ADO rejected the token."
        if e.code == 403:
            return False, f"Access denied to project '{project}' in '{org}'."
        if e.code == 404:
            return False, f"Project '{project}' not found in organization '{org}'."
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize ~/.az-workitems/config.json"
    )
    parser.add_argument(
        "--org",
        default=DEFAULT_ORG,
        help=f"Azure DevOps organization name (default: {DEFAULT_ORG})",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help=f"Azure DevOps project name (default: {DEFAULT_PROJECT})",
    )
    args = parser.parse_args()

    org: str = args.org
    project: str = args.project

    print("Acquiring an Azure DevOps access token via the Azure CLI...")
    token, error = fetch_cli_token()
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(AZ_LOGIN_HINT, file=sys.stderr)
        return 1

    print("Validating the token against Azure DevOps...")
    ok, error = validate_token(org, project, token)
    if not ok:
        print(f"ERROR: Validation failed — {error}", file=sys.stderr)
        return 1

    print("Token validated successfully.")
    print()

    save_config({"organization": org, "project": project, "token": token})

    print(f"Config written to {CONFIG_PATH}")
    print(f"Organization: {org}")
    print(f"Project: {project}")

    expiry_text = local_expiry_text(token)
    if expiry_text:
        print(f"Token expires: {expiry_text}")
    print("Later runs refresh the token automatically as it nears expiry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
