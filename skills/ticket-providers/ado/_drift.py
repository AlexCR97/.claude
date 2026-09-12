#!/usr/bin/env python3
"""
Reports what changed on an Azure DevOps work item since it was last fetched.

Coming back after days away, the local raw.json may no longer describe the work
item: the state moved, the acceptance criteria were edited, someone answered a
question in the discussion. Re-fetching everything to find out is slow and
overwrites nothing useful when nothing changed, so this compares a handful of
cheap signals and lets the caller decide whether a re-fetch is worth it.

Read-only against both ADO and the local data — raw.json is never rewritten.
"""

import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from ticketlib import config, http, paths
from ticketlib.errors import EXIT_ERROR, TicketError

API_VERSION = "7.1"
COMMENTS_API_VERSION = "7.1-preview.4"

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

AUTH_HINT = "Re-run 'az login' and try again."


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


def read_local(raw_path: Path, ticket_id: str) -> dict:
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TicketError(
            f"no fetched data at {raw_path}",
            EXIT_ERROR,
            f"Run `/ticket-fetch ado:{ticket_id}` before resuming.",
        ) from exc
    except (json.JSONDecodeError, OSError) as exc:
        raise TicketError(f"could not read {raw_path} — {exc}") from exc

    tree = raw.get("tree") or {}
    work_item = tree.get("work_item") or {}
    discussion = tree.get("discussion") or {}
    comments = discussion.get("comments") or []

    return {
        "meta": raw.get("meta") or {},
        "rev": work_item.get("rev"),
        "fields": work_item.get("fields") or {},
        "comment_count": discussion.get("totalCount", len(comments)),
        "comment_ids": {comment.get("id") for comment in comments},
    }


def fetch_live(ticket_id: str, org: str, project: str, header: str) -> dict:
    fields = ",".join(TRACKED_FIELDS)
    project_encoded = urllib.parse.quote(project, safe="")

    try:
        work_item = http.get_json(
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{ticket_id}"
            f"?fields={fields}&api-version={API_VERSION}",
            header,
            AUTH_HINT,
        )
        comments = http.get_json(
            f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
            f"/{ticket_id}/comments?api-version={COMMENTS_API_VERSION}",
            header,
            AUTH_HINT,
        )
    except http.NETWORK_ERRORS as exc:
        raise TicketError(f"could not reach Azure DevOps — {exc}") from exc

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


def run(ticket_id: str, header: str, record: dict) -> dict:
    raw_path = paths.ticket_dir("ado", ticket_id) / "raw" / "raw.json"
    local = read_local(raw_path, ticket_id)

    stored = config.load_source("ado")
    org = local["meta"].get("organization") or stored.get("organization")
    project = local["meta"].get("project") or stored.get("project")
    if not org or not project:
        raise TicketError(
            "could not determine the ADO organization and project",
            EXIT_ERROR,
            "Run `/ticket-init ado` first.",
        )

    live = fetch_live(ticket_id, str(org), str(project), header)

    field_changes = diff_fields(local["fields"], live["fields"])
    added_comments = new_comments(live["comments"], local["comment_ids"])
    revision_changed = (
        local["rev"] is not None
        and live["rev"] is not None
        and local["rev"] != live["rev"]
    )

    fetched_at = record.get("last_fetched_at") or ""
    changed_at = display_name(live["fields"].get("System.ChangedDate"))

    return {
        "is_stale": bool(field_changes or added_comments or revision_changed),
        "organization": org,
        "project": project,
        "fetched_at": fetched_at,
        "fetched_days_ago": age_in_days(parse_iso(fetched_at)),
        "changed_at": changed_at,
        "changed_days_ago": age_in_days(parse_iso(changed_at)),
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
