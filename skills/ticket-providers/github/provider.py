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

from ticketlib import providers, tickets
from ticketlib.errors import EXIT_ERROR, TicketError

SOURCE = "github"

# owner/name. A third segment would be a cross-repo reference, which a product
# bound to one repository cannot express — see README.md.
REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

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

# The label that makes `LABEL_TYPE_MAP` read a created issue back as the type it
# was created as. A task has none: it is what an unlabelled issue falls back to.
NATIVE_LABEL_BY_TYPE = {
    "bug": "bug",
    "spike": "spike",
    "tech-debt": "tech-debt",
    "user-story": "enhancement",
}

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


def binding(ctx: dict, extra: list[str]) -> dict:
    """
    The owner and repository an init would bind, without validating them.

    `--repo name` alone is enough where the namespace is already bound to an
    owner. With no flag, the repository the invocation directory belongs to.
    """
    parser = argparse.ArgumentParser(prog="ticket.py init --source github")
    parser.add_argument("--repo", "--repository", dest="repo")
    args = parser.parse_args(extra)

    inherited = ctx.get("binding") or {}
    inherited_applied: list[str] = []
    repo = args.repo

    if repo and NAME_PATTERN.match(repo) and inherited.get("owner"):
        repo = f"{inherited['owner']}/{repo}"
        inherited_applied.append("owner")
    if not repo and inherited.get("owner") and inherited.get("repository"):
        repo = f"{inherited['owner']}/{inherited['repository']}"
        inherited_applied.extend(["owner", "repository"])
    if not repo:
        _gh.require_cli()
        repo = detect_repo()
    if not repo:
        raise TicketError(
            "no repository given and none could be detected",
            EXIT_ERROR,
            "Pass --repo owner/name, or run this from inside a worktree of the GitHub repository.",
        )
    if not REPO_PATTERN.match(repo):
        raise TicketError(
            f"'{repo}' is not an owner/name repository",
            EXIT_ERROR,
            "Cross-repository references are out of scope; see ticket-providers/README.md.",
        )

    owner, _, name = repo.partition("/")
    return {
        "coordinates": {"owner": owner, "repository": name},
        "defaults_applied": [],
        "inherited": inherited_applied,
    }


def init(ctx: dict, extra: list[str]) -> dict:
    _gh.require_cli()
    repo = _gh.repository(ctx)

    print("Checking the GitHub CLI's authentication…")
    _gh.require_auth()

    print(f"Validating access to {repo}…")
    _gh.api(f"repos/{repo}")

    # Only the owner and repository are bound. There is no token here, by design.
    return {"repository": repo, "credential": "delegated to the GitHub CLI; nothing stored"}


def detect_repo() -> str | None:
    code, stdout, _ = _gh.run(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    return stdout.strip() if code == 0 and stdout.strip() else None


def fetch(ctx: dict, extra: list[str]) -> dict:
    ticket_id = ctx["id"]
    repo = _gh.repository(ctx)

    out_dir = ctx["location"].dir / "raw"
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

    owner, _, name = repo.partition("/")
    tickets.update(
        ctx["location"],
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
        coordinates={"owner": owner, "repository": name},
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
