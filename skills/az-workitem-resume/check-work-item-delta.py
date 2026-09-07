#!/usr/bin/env python3
"""
Reports what changed on an Azure DevOps work item since it was last fetched.

Coming back to a work item after days away, the local raw/raw.json may no
longer describe the work item: the state moved, the acceptance criteria were
edited, someone answered a question in the discussion. Re-fetching everything
to find out is slow and overwrites nothing useful when nothing changed, so this
compares a handful of cheap signals first and lets az-workitem-resume decide
whether a re-fetch is worth it.

Read-only against both ADO and the local data — raw.json is never rewritten.

Usage:
    python check-work-item-delta.py --id 12345 [--org ORG] [--project PROJECT]

The organization and project default to the ones recorded in the local
raw.json's meta block, so the comparison is always against the same coordinates
the fetch used. config.json is the fallback when meta lacks them.

Output: a single JSON object on stdout.

Exit codes:
    0  the local copy is up to date
    1  the comparison could not be made (no raw.json, no credential, network)
    2  the work item changed since the last fetch
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# 'az-workitem-common' is not an importable package name, so add it to sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent / "az-workitem-common"))

from ado_auth import load_config, make_auth_header, require_token

EXIT_UP_TO_DATE = 0
EXIT_ERROR = 1
EXIT_STALE = 2

# Fields whose change is worth surfacing in a resume briefing. Everything else
# on a work item can move without altering what the developer should do next.
TRACKED_FIELDS = (
    "System.Title",
    "System.State",
    "System.ChangedDate",
    "System.ChangedBy",
    "System.AssignedTo",
    "System.IterationPath",
    "System.Tags",
    "Microsoft.VSTS.Common.AcceptanceCriteria",
    "System.Description",
)

# Long enough to tell whether a comment answers an open question, short enough
# that the briefing stays readable. The full text is one re-fetch away.
COMMENT_SNIPPET_LIMIT = 400

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Fields holding HTML bodies: report that they changed, never how, since a
# rendered diff of markup belongs in the browser rather than a briefing.
HTML_FIELDS = frozenset(
    {"Microsoft.VSTS.Common.AcceptanceCriteria", "System.Description"}
)

# Fields that move as a consequence of some other edit rather than being the
# edit. Reported as context ("changed by X, 2 days ago"), never as diff rows:
# a row reading "ChangedBy: Ana -> Bob" says who typed, not what changed, and
# the revision delta already reports that something did.
CONSEQUENCE_FIELDS = frozenset({"System.ChangedDate", "System.ChangedBy"})


def fail(message: str, hint: str = "") -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    if hint:
        print(hint, file=sys.stderr)
    raise SystemExit(EXIT_ERROR)


def get(url: str, token: dict) -> dict:
    request = urllib.request.Request(
        url, headers={"Authorization": make_auth_header(token)}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def strip_html(html: str) -> str:
    text = HTML_TAG_PATTERN.sub(" ", html or "")
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return re.sub(r"\s+", " ", text).strip()


def display_name(value: object) -> str:
    """An identity field is an object; every other tracked field is a string."""
    if isinstance(value, dict):
        return str(value.get("displayName") or "")
    return "" if value is None else str(value)


def summarize(value: object, field: str) -> str:
    if field in HTML_FIELDS:
        text = strip_html(display_name(value))
        return f"{text[:80]}…" if len(text) > 80 else text
    return display_name(value)


def parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def age_in_days(moment: datetime | None) -> float | None:
    if moment is None:
        return None
    return round((datetime.now(timezone.utc) - moment).total_seconds() / 86400, 1)


def read_local(raw_path: Path, work_item_id: int) -> dict:
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(
            f"no fetched data at {raw_path}",
            f"Run /az-workitem-fetch {work_item_id} before resuming.",
        )
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"could not read {raw_path} — {exc}")

    tree = raw.get("tree") or {}
    work_item = tree.get("work_item") or {}
    discussion = tree.get("discussion") or {}
    comments = discussion.get("comments") or []

    # raw.json is rewritten on every fetch, so its mtime is the fetch time.
    try:
        fetched_at = datetime.fromtimestamp(
            raw_path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
    except OSError:
        fetched_at = ""

    return {
        "meta": raw.get("meta") or {},
        "rev": work_item.get("rev"),
        "fields": work_item.get("fields") or {},
        "comment_count": discussion.get("totalCount", len(comments)),
        "comment_ids": {comment.get("id") for comment in comments},
        "fetched_at": fetched_at,
    }


def resolve_coordinates(args: argparse.Namespace, local_meta: dict) -> tuple[str, str]:
    config = load_config()
    org = args.org or local_meta.get("organization") or config.get("organization")
    project = args.project or local_meta.get("project") or config.get("project")

    if not org or not project:
        fail(
            "could not determine the ADO organization and project",
            "Pass --org and --project, or run /az-workitem-init first.",
        )

    return str(org), str(project)


def fetch_live(work_item_id: int, org: str, project: str, token: dict) -> dict:
    fields = ",".join(TRACKED_FIELDS)
    project_encoded = urllib.parse.quote(project, safe="")

    try:
        work_item = get(
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{work_item_id}"
            f"?fields={fields}&api-version=7.1",
            token,
        )
        comments = get(
            f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
            f"/{work_item_id}/comments?api-version=7.1-preview.4",
            token,
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            fail(
                "Azure DevOps rejected the credential (HTTP 401).",
                "Re-run 'az login' and try again.",
            )
        if exc.code == 404:
            fail(f"work item {work_item_id} was not found in {org}/{project}.")
        fail(f"Azure DevOps returned HTTP {exc.code} — {exc.reason}")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        fail(f"could not reach Azure DevOps — {exc}")

    return {
        "rev": work_item.get("rev"),
        "fields": work_item.get("fields") or {},
        "comments": comments.get("comments") or [],
        "comment_count": comments.get(
            "totalCount", len(comments.get("comments") or [])
        ),
    }


def diff_fields(local_fields: dict, live_fields: dict) -> list[dict]:
    changes = []
    for field in TRACKED_FIELDS:
        if field in CONSEQUENCE_FIELDS:
            continue

        before = summarize(local_fields.get(field), field)
        after = summarize(live_fields.get(field), field)
        if before != after:
            changes.append({"field": field, "before": before, "after": after})

    return changes


def new_comments(live_comments: list[dict], known_ids: set) -> list[dict]:
    added = []
    for comment in live_comments:
        if comment.get("id") in known_ids:
            continue

        text = strip_html(comment.get("text") or "")
        added.append(
            {
                "id": comment.get("id"),
                "author": display_name(comment.get("createdBy")),
                "date": comment.get("modifiedDate") or comment.get("createdDate"),
                "snippet": (
                    f"{text[:COMMENT_SNIPPET_LIMIT]}…"
                    if len(text) > COMMENT_SNIPPET_LIMIT
                    else text
                ),
            }
        )

    added.sort(key=lambda comment: comment.get("date") or "")
    return added


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report what changed on an ADO work item since it was fetched."
    )
    parser.add_argument("--id", required=True, type=int, help="Work item ID")
    parser.add_argument("--org", help="ADO organization (default: from raw.json)")
    parser.add_argument("--project", help="ADO project (default: from raw.json)")
    args = parser.parse_args()

    raw_path = Path.home() / ".az-workitems" / str(args.id) / "raw" / "raw.json"
    local = read_local(raw_path, args.id)
    org, project = resolve_coordinates(args, local["meta"])

    token = require_token()
    live = fetch_live(args.id, org, project, token)

    field_changes = diff_fields(local["fields"], live["fields"])
    added_comments = new_comments(live["comments"], local["comment_ids"])
    revision_changed = (
        local["rev"] is not None
        and live["rev"] is not None
        and local["rev"] != live["rev"]
    )

    is_stale = bool(field_changes or added_comments or revision_changed)

    fetched_at = parse_iso(local["fetched_at"])
    changed_at = parse_iso(display_name(live["fields"].get("System.ChangedDate")))

    result = {
        "work_item_id": args.id,
        "organization": org,
        "project": project,
        "is_stale": is_stale,
        "fetched_at": local["fetched_at"],
        "fetched_days_ago": age_in_days(fetched_at),
        "changed_at": display_name(live["fields"].get("System.ChangedDate")),
        "changed_days_ago": age_in_days(changed_at),
        "changed_by": display_name(live["fields"].get("System.ChangedBy")),
        "revision": {
            "local": local["rev"],
            "live": live["rev"],
            "changed": revision_changed,
        },
        "title": display_name(live["fields"].get("System.Title")),
        "state": display_name(live["fields"].get("System.State")),
        "field_changes": field_changes,
        "new_comment_count": len(added_comments),
        "new_comments": added_comments,
        "comment_count": {
            "local": local["comment_count"],
            "live": live["comment_count"],
        },
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(EXIT_STALE if is_stale else EXIT_UP_TO_DATE)


if __name__ == "__main__":
    main()
