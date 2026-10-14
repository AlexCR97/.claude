#!/usr/bin/env python3
"""
Changing an Azure DevOps work item.

The write is a JSON Patch that opens with a `test` on the work item's revision.
Azure DevOps rejects the whole patch when the revision has moved, so an edit
made by someone else between the drift check and this write is refused rather
than overwritten — the drift check narrows the window, the revision closes it.
"""

import json
import urllib.parse
from pathlib import Path

from ticketlib import http
from ticketlib.errors import EXIT_ERROR, TicketError

API_VERSION = "7.1"

AUTH_HINT = "If it came from the Azure CLI it has expired — re-run 'az login' and try again."

TITLE_FIELD = "System.Title"
DESCRIPTION_FIELD = "System.Description"
CRITERIA_FIELD = "Microsoft.VSTS.Common.AcceptanceCriteria"
STATE_FIELD = "System.State"
TAGS_FIELD = "System.Tags"

FIELD_BY_CHANGE = {
    "title": TITLE_FIELD,
    "description": DESCRIPTION_FIELD,
    "acceptance_criteria": CRITERIA_FIELD,
    "state": STATE_FIELD,
}


def read_snapshot(ticket_dir_owner, ticket_id: str) -> dict:
    """The root work item as last fetched: its revision, fields and project."""
    raw_path = Path(ticket_dir_owner.dir) / "raw" / "raw.json"
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise TicketError(
            f"no fetched data at {raw_path}",
            EXIT_ERROR,
            f"Run `/ticket-fetch ado:{ticket_id}` first.",
        ) from exc

    work_item = (raw.get("tree") or {}).get("work_item") or {}
    if work_item.get("rev") is None:
        raise TicketError(
            f"the snapshot of ado:{ticket_id} carries no revision",
            EXIT_ERROR,
            f"Run `/ticket-fetch ado:{ticket_id}` to refresh it.",
        )
    return {
        "rev": work_item["rev"],
        "fields": work_item.get("fields") or {},
        "project": (raw.get("meta") or {}).get("project"),
    }


def patch_document(revision: int, changes: list[dict]) -> list[dict]:
    operations: list[dict] = [{"op": "test", "path": "/rev", "value": revision}]
    for change in changes:
        if change["field"] == "labels":
            operations.append(
                {"op": "add", "path": f"/fields/{TAGS_FIELD}", "value": "; ".join(change["after"])}
            )
        else:
            operations.append(
                {"op": "add", "path": f"/fields/{FIELD_BY_CHANGE[change['field']]}", "value": change["after"]}
            )
    return operations


def write(org: str, project: str, ticket_id: str, header: str, operations: list[dict]) -> dict:
    url = (
        f"https://dev.azure.com/{org}/{urllib.parse.quote(project, safe='')}"
        f"/_apis/wit/workitems/{ticket_id}?api-version={API_VERSION}"
    )
    return http.post_json(
        url,
        header,
        operations,
        AUTH_HINT,
        content_type="application/json-patch+json",
        method="PATCH",
    )
