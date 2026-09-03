#!/usr/bin/env python3
"""
Posts a refinement comment to an Azure DevOps work item discussion via the
REST API. The comment text is read from a file passed as --comment-file.
The file must contain HTML, as ADO discussion renders HTML only.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# 'az-workitem-common' is not an importable package name, so add it to sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent / "az-workitem-common"))

from ado_auth import make_auth_header, require_token


def post_comment(org: str, project: str, wi_id: int, token: dict, text: str) -> dict:
    project_encoded = urllib.parse.quote(project, safe="")
    url = (
        f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
        f"/{wi_id}/comments?api-version=7.1-preview.4"
    )
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": make_auth_header(token),
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"ERROR: HTTP {e.code} — {e.reason}\n{body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error — {e.reason}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post a refinement comment to an ADO work item."
    )
    parser.add_argument("--id", required=True, type=int, help="Work item ID")
    parser.add_argument("--org", required=True, help="ADO organization name")
    parser.add_argument("--project", required=True, help="ADO project name")
    parser.add_argument(
        "--comment-file",
        required=True,
        help="Path to a file containing the comment text (HTML or plain text); "
        "a leading ~ is expanded to the user's home directory",
    )
    parser.add_argument(
        "--delete-after-post",
        action="store_true",
        help="Delete the comment file after it is successfully posted",
    )
    args = parser.parse_args()

    # expanduser() so callers can pass ~/.az-workitems/... — neither Python nor
    # a quoted PowerShell argument expands the tilde on its own.
    comment_path = Path(args.comment_file).expanduser()
    if not comment_path.exists():
        print(f"ERROR: comment file not found: {comment_path}", file=sys.stderr)
        sys.exit(1)

    text = comment_path.read_text(encoding="utf-8").strip()
    if not text:
        print("ERROR: comment file is empty.", file=sys.stderr)
        sys.exit(1)

    token = require_token()

    result = post_comment(args.org, args.project, args.id, token, text)
    comment_id = result.get("id")
    print(f"Comment posted successfully (id={comment_id}).")

    if args.delete_after_post:
        comment_path.unlink()
        print(f"Deleted {comment_path}.")


if __name__ == "__main__":
    main()
