#!/usr/bin/env python3
"""
Initializes the ~/.az-workitems directory and config.json for Azure DevOps work item skills.
"""

import argparse
import base64
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_ORG = "edwire"
DEFAULT_PROJECT = "EW.Educate"

# Well-known Azure DevOps resource ID — an access token issued for it is accepted
# by the ADO REST API as the password in basic auth, exactly like a PAT.
AZURE_DEVOPS_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"


def fetch_default_token() -> tuple[str, str]:
    """
    Acquire an Azure DevOps access token via the Azure CLI.
    Returns (token, error_message); token is empty when acquisition failed.
    """
    # Resolve the executable explicitly: on Windows 'az' is a .cmd shim, which
    # CreateProcess will not find from the bare name the way PATHEXT does.
    executable = shutil.which("az")
    if not executable:
        return "", "Azure CLI ('az') not found on PATH."

    command = [
        executable,
        "account",
        "get-access-token",
        "--resource",
        AZURE_DEVOPS_RESOURCE_ID,
        "--query",
        "accessToken",
        "--output",
        "tsv",
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
        return "", "Azure CLI timed out while acquiring an access token."

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        return "", f"Azure CLI failed to acquire an access token — {detail}"

    token = result.stdout.strip()
    if not token:
        return "", "Azure CLI returned an empty access token."

    return token, ""


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
    parser.add_argument(
        "--pat",
        help="Personal Access Token (default: an Azure CLI access token for Azure DevOps)",
    )
    args = parser.parse_args()

    org: str = args.org
    project: str = args.project
    pat: str = args.pat or ""

    if not pat:
        print("Acquiring an Azure DevOps access token via the Azure CLI...")
        pat, error = fetch_default_token()
        if not pat:
            print(f"ERROR: {error}", file=sys.stderr)
            print(
                "Run 'az login' or pass --pat with a Personal Access Token.",
                file=sys.stderr,
            )
            return 1

    print()
    print("Validating credentials against Azure DevOps...")
    ok, error = validate_credentials(org, project, pat)
    if not ok:
        print(f"ERROR: Validation failed — {error}", file=sys.stderr)
        return 1

    print("Credentials validated successfully.")
    print()

    # Config is machine-wide, not per-workspace: Path.home() resolves to
    # %USERPROFILE% on Windows and $HOME on Linux/macOS.
    workitems_dir = Path.home() / ".az-workitems"
    workitems_dir.mkdir(parents=True, exist_ok=True)
    config = {"organization": org, "project": project, "pat": pat}
    (workitems_dir / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    print(f"Config written to {workitems_dir / 'config.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
