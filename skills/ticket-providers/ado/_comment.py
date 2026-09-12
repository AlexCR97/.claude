#!/usr/bin/env python3
"""
Posts a comment to an Azure DevOps work item discussion via the REST API.

The text must be HTML: the ADO discussion renderer accepts nothing else, and a
markdown body posted here arrives as escaped source rather than formatting.
"""

import urllib.parse

from ticketlib import http

COMMENTS_API_VERSION = "7.1-preview.4"

AUTH_HINT = "Re-run 'az login' and try again."


def run(ticket_id: str, org: str, project: str, header: str, text: str) -> dict:
    project_encoded = urllib.parse.quote(project, safe="")
    url = (
        f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
        f"/{ticket_id}/comments?api-version={COMMENTS_API_VERSION}"
    )

    result = http.post_json(url, header, {"text": text}, AUTH_HINT)
    comment_id = result.get("id")

    return {
        "comment_id": comment_id,
        "url": f"https://dev.azure.com/{org}/{urllib.parse.quote(project)}"
        f"/_workitems/edit/{ticket_id}#{comment_id}",
    }
