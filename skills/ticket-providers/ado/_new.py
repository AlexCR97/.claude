#!/usr/bin/env python3
"""
Creating an Azure DevOps work item.

The native type a canonical type is created as depends on the project's process
template — Agile calls a story "User Story", Scrum calls it "Product Backlog
Item" — so the candidates in `types.md` are checked against the types the
project actually has, never assumed.
"""

import urllib.parse

from ticketlib import azrest
from ticketlib.errors import EXIT_ERROR, TicketError

# Most specific first. Spike and tech debt are not native types here, so they are
# created as a task and told apart by the tag in TAG_BY_TYPE.
NATIVE_CANDIDATES = {
    "user-story": ("User Story", "Product Backlog Item", "Requirement", "Feature"),
    "bug": ("Bug", "Defect"),
    "task": ("Task", "Issue"),
    "spike": ("Task", "Issue"),
    "tech-debt": ("Task", "Issue"),
}

TAG_BY_TYPE = {"spike": "spike", "tech-debt": "tech-debt"}

PARENT_RELATION = "System.LinkTypes.Hierarchy-Reverse"

DESCRIPTION_FIELD = "System.Description"
CRITERIA_FIELD = "Microsoft.VSTS.Common.AcceptanceCriteria"


def project_types(org: str, project: str) -> list[str]:
    url = (
        f"https://dev.azure.com/{org}/{urllib.parse.quote(project, safe='')}"
        "/_apis/wit/workitemtypes"
    )
    payload = azrest.get_json(url)
    return [str(entry.get("name")) for entry in payload.get("value") or [] if entry.get("name")]


def native_type(canonical: str, available: list[str]) -> str:
    lowered = {name.lower(): name for name in available}
    for candidate in NATIVE_CANDIDATES.get(canonical, ()):
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    raise TicketError(
        f"the project has no work item type that '{canonical}' can be created as",
        EXIT_ERROR,
        "It has: " + ", ".join(available) + ". Add the type to NATIVE_CANDIDATES in _new.py.",
    )


def patch_document(
    org: str,
    title: str,
    description: str,
    criteria: str,
    tags: list[str],
    parent_id: str | None,
) -> list[dict]:
    operations = [{"op": "add", "path": "/fields/System.Title", "value": title}]
    if description:
        operations.append(
            {"op": "add", "path": f"/fields/{DESCRIPTION_FIELD}", "value": description}
        )
    if criteria:
        operations.append(
            {"op": "add", "path": f"/fields/{CRITERIA_FIELD}", "value": criteria}
        )
    if tags:
        operations.append(
            {"op": "add", "path": "/fields/System.Tags", "value": "; ".join(tags)}
        )
    if parent_id:
        operations.append(
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": PARENT_RELATION,
                    "url": f"https://dev.azure.com/{org}/_apis/wit/workItems/{parent_id}",
                },
            }
        )
    return operations


def create(org: str, project: str, native: str, operations: list[dict]) -> dict:
    url = (
        f"https://dev.azure.com/{org}/{urllib.parse.quote(project, safe='')}"
        f"/_apis/wit/workitems/${urllib.parse.quote(native, safe='')}"
    )
    return azrest.send_json(
        "post", url, operations, content_type="application/json-patch+json"
    )
