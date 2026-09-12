#!/usr/bin/env python3
"""
The GitHub provider's entry points.

Two gaps are declared rather than worked around: `capabilities.related` is
false, because an issue's cross-references are prose rather than a typed link
structure, and `capabilities.attachments` is false, because an issue body
references uploaded files by URL with no enumerable attachment list.
"""

import argparse
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ticketlib import config, paths, providers, tickets
from ticketlib.errors import EXIT_ERROR, TicketError

SOURCE = "github"

# owner/name. A third segment would be a cross-repo reference, which the
# `github/{number}/` layout cannot express — see README.md.
REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")

# GitHub has no type field, so a label is the only signal there is.
LABEL_TYPE_MAP = {
    "bug": "bug",
    "defect": "bug",
    "spike": "spike",
    "research": "spike",
    "investigation": "spike",
    "tech-debt": "tech-debt",
    "techdebt": "tech-debt",
    "tech debt": "tech-debt",
    "technical debt": "tech-debt",
    "refactor": "tech-debt",
    "enhancement": "user-story",
    "feature": "user-story",
    "story": "user-story",
}

FALLBACK_TYPE = "task"

_gh = providers.load_private(SOURCE, "_gh")


def resolve_type(issue: dict) -> tuple[str, str, str]:
    """Returns (canonical_type, native_type, note); note is empty when certain."""
    labels = [
        str((label or {}).get("name") or "").strip().lower()
        for label in issue.get("labels") or []
    ]

    for label in labels:
        if label in LABEL_TYPE_MAP:
            return LABEL_TYPE_MAP[label], ", ".join(labels), f"label '{label}' selected the type"

    return (
        FALLBACK_TYPE,
        ", ".join(labels),
        "no label maps to a canonical type — falling back to "
        f"'{FALLBACK_TYPE}' (this source has no type field)",
    )


def init(ctx: dict, extra: list[str]) -> dict:
    parser = argparse.ArgumentParser(prog="ticket.py init --source github")
    parser.add_argument("--repo", "--repository", dest="repo")
    args = parser.parse_args(extra)

    _gh.require_cli()

    repo = args.repo or detect_repo()
    if not repo:
        raise TicketError(
            "no repository given and none could be detected",
            EXIT_ERROR,
            "Pass --repo owner/name, or run this from inside a GitHub clone.",
        )
    if not REPO_PATTERN.match(repo):
        raise TicketError(
            f"'{repo}' is not an owner/name repository",
            EXIT_ERROR,
            "Cross-repository references are out of scope; see ticket-providers/README.md.",
        )

    print("Checking the GitHub CLI's authentication…")
    _gh.require_auth()

    print(f"Validating access to {repo}…")
    _gh.api(f"repos/{repo}")

    # Only the repository is stored. There is no token here, by design.
    config.save_source(SOURCE, {"repository": repo})

    return {"repository": repo, "credential": "delegated to the GitHub CLI; nothing stored"}


def detect_repo() -> str | None:
    code, stdout, _ = _gh.run(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    return stdout.strip() if code == 0 and stdout.strip() else None


def fetch(ctx: dict, extra: list[str]) -> dict:
    ticket_id = ctx["id"]
    repo = _gh.repository()

    out_dir = paths.ticket_dir(SOURCE, ticket_id) / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {repo}#{ticket_id}…")
    issue = _gh.api(f"repos/{repo}/issues/{ticket_id}")
    comments = _gh.api(f"repos/{repo}/issues/{ticket_id}/comments", paginate=True)
    if not isinstance(comments, list):
        comments = []
    print(f"  {len(comments)} comment(s)")

    raw = {
        "meta": {
            "repository": repo,
            "issue_number": int(ticket_id),
            "related_supported": False,
        },
        "issue": issue,
        "comments": comments,
    }

    json_path = out_dir / "raw.json"
    json_path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    canonical_type, native_type, note = resolve_type(issue)

    tickets.update(
        SOURCE,
        ticket_id,
        title=issue.get("title"),
        state=issue.get("state"),
        type=canonical_type,
        native_type=native_type,
        url=issue.get("html_url"),
        last_fetched_at=tickets.now_iso(),
        fingerprint={
            "updated_at": issue.get("updated_at"),
            "comment_count": len(comments),
        },
    )

    return {
        "raw_json": str(json_path),
        "comment_count": len(comments),
        "type": canonical_type,
        "native_type": native_type,
        "type_note": note,
        "attachments_kept": 0,
        "attachments_downloaded": 0,
        "attachments_failed": [],
    }


def publish(ctx: dict, text: str, extra: list[str]) -> dict:
    repo = _gh.repository()
    _gh.require_auth()

    # `gh issue comment` takes a file rather than an argument, which also keeps
    # a long markdown body off the command line.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(text)
        body_path = Path(handle.name)

    try:
        code, stdout, stderr = _gh.run(
            [
                "issue",
                "comment",
                str(ctx["id"]),
                "--repo",
                repo,
                "--body-file",
                str(body_path),
            ]
        )
    finally:
        body_path.unlink(missing_ok=True)

    if code != 0:
        raise TicketError(
            f"could not post the comment — {stderr.strip() or f'exit code {code}'}"
        )

    return {"repository": repo, "url": stdout.strip() or None}


def drift(ctx: dict, extra: list[str]) -> dict:
    ticket_id = ctx["id"]
    repo = _gh.repository()
    record = tickets.load(SOURCE, ticket_id)

    raw_path = paths.ticket_dir(SOURCE, ticket_id) / "raw" / "raw.json"
    local = config.read_json(raw_path)
    if not local:
        raise TicketError(
            f"no fetched data at {raw_path}",
            EXIT_ERROR,
            f"Run `/ticket-fetch github:{ticket_id}` before resuming.",
        )

    local_issue = local.get("issue") or {}
    local_comments = local.get("comments") or []
    known_ids = {comment.get("id") for comment in local_comments}

    live_issue = _gh.api(f"repos/{repo}/issues/{ticket_id}")
    live_comments = _gh.api(f"repos/{repo}/issues/{ticket_id}/comments", paginate=True)
    if not isinstance(live_comments, list):
        live_comments = []

    field_changes = []
    for key, label in (("title", "title"), ("state", "state"), ("body", "body")):
        before, after = local_issue.get(key), live_issue.get(key)
        if before == after:
            continue
        if key == "body":
            # A body diff belongs in the browser; report only that it moved.
            field_changes.append({"field": "body", "before": "(changed)", "after": "(changed)"})
        else:
            field_changes.append({"field": label, "before": before, "after": after})

    local_labels = sorted(
        str((label or {}).get("name") or "") for label in local_issue.get("labels") or []
    )
    live_labels = sorted(
        str((label or {}).get("name") or "") for label in live_issue.get("labels") or []
    )
    if local_labels != live_labels:
        field_changes.append(
            {
                "field": "labels",
                "before": ", ".join(local_labels),
                "after": ", ".join(live_labels),
            }
        )

    new_comments = [
        {
            "id": comment.get("id"),
            "author": (comment.get("user") or {}).get("login"),
            "date": comment.get("updated_at") or comment.get("created_at"),
            "snippet": snippet(comment.get("body") or ""),
        }
        for comment in live_comments
        if comment.get("id") not in known_ids
    ]
    new_comments.sort(key=lambda comment: comment.get("date") or "")

    updated_changed = local_issue.get("updated_at") != live_issue.get("updated_at")

    return {
        "is_stale": bool(field_changes or new_comments or updated_changed),
        "repository": repo,
        "fetched_at": record.get("last_fetched_at"),
        "changed_at": live_issue.get("updated_at"),
        "changed_days_ago": age_in_days(live_issue.get("updated_at")),
        "title": live_issue.get("title"),
        "state": live_issue.get("state"),
        "revision": {
            "local": local_issue.get("updated_at"),
            "live": live_issue.get("updated_at"),
            "changed": updated_changed,
        },
        "field_changes": field_changes,
        "new_comment_count": len(new_comments),
        "new_comments": new_comments,
        "comment_count": {"local": len(local_comments), "live": len(live_comments)},
    }


# Long enough to tell whether a comment answers an open question, short enough
# that a briefing stays readable.
COMMENT_SNIPPET_LIMIT = 400


def snippet(body: str) -> str:
    text = " ".join(body.split())
    return f"{text[:COMMENT_SNIPPET_LIMIT]}…" if len(text) > COMMENT_SNIPPET_LIMIT else text


def age_in_days(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((datetime.now(timezone.utc) - moment).total_seconds() / 86400, 1)


def auth_status(ctx: dict) -> dict:
    signed_in, detail = _gh.auth_state()
    return {
        "repository": config.load_source(SOURCE).get("repository"),
        "credential": "delegated to the GitHub CLI; nothing stored",
        "status": detail or ("signed in" if signed_in else "not signed in"),
        "usable": signed_in,
    }
