#!/usr/bin/env python3
"""
Fetches a complete Azure DevOps work item and dumps all raw data (fields,
comments, relations, attachments) into raw/raw.json plus downloaded attachment
files, then refreshes ticket.json.

Related work items are fetched recursively up to MAX_DEPTH levels deep.
Already-visited ids are tracked to prevent cycles.

Attachment naming:
  - Files are named after their ADO attachment GUID plus the original
    extension, because ADO names every pasted screenshot "image.png".

Re-fetch behavior:
  - raw.json is always re-downloaded.
  - Naming is deterministic, so a file already on disk is the same attachment
    and is kept, NOT re-downloaded.
  - New attachments are downloaded normally.
"""

import json
import re
import sys
import urllib.parse
import zipfile
from pathlib import Path

from ticketlib import http, paths, tickets
from ticketlib.http import NETWORK_ERRORS

API_VERSION = "7.1"
COMMENTS_API_VERSION = "7.1-preview.4"

MAX_DEPTH = 3

RELATION_TYPES = {
    "System.LinkTypes.Hierarchy-Reverse": "parent",
    "System.LinkTypes.Hierarchy-Forward": "child",
    "System.LinkTypes.Related": "related",
}

# A Task's children and siblings are almost never the context its own work
# needs, and expanding them pulls in the whole sprint.
TASK_RELATIONS = frozenset({"parent"})
FULL_RELATIONS = frozenset({"parent", "child", "related"})

AUTH_HINT = "If it came from the Azure CLI it has expired — re-run 'az login' and try again."

# The work item type this source calls a thing, mapped onto a canonical type.
NATIVE_TYPE_MAP = {
    "user story": "user-story",
    "product backlog item": "user-story",
    "feature": "user-story",
    "epic": "user-story",
    "requirement": "user-story",
    "bug": "bug",
    "defect": "bug",
    "task": "task",
    "issue": "task",
}

# A tag wins over the work item type, because neither Spike nor Tech Debt is a
# native type here and a tag is the only way anyone can say so.
TAG_TYPE_MAP = {
    "spike": "spike",
    "research": "spike",
    "investigation": "spike",
    "tech-debt": "tech-debt",
    "techdebt": "tech-debt",
    "tech debt": "tech-debt",
    "technical debt": "tech-debt",
    "refactor": "tech-debt",
}

FALLBACK_TYPE = "task"


def resolve_type(fields: dict) -> tuple[str, str, str]:
    """Returns (canonical_type, native_type, note); note is empty when certain."""
    native = str(fields.get("System.WorkItemType") or "")

    tags = [
        tag.strip().lower()
        for tag in str(fields.get("System.Tags") or "").split(";")
        if tag.strip()
    ]
    for tag in tags:
        if tag in TAG_TYPE_MAP:
            return TAG_TYPE_MAP[tag], native, f"tag '{tag}' overrides work item type '{native}'"

    mapped = NATIVE_TYPE_MAP.get(native.strip().lower())
    if mapped:
        return mapped, native, ""

    return (
        FALLBACK_TYPE,
        native,
        f"work item type '{native or 'unknown'}' maps to no canonical type — "
        f"falling back to '{FALLBACK_TYPE}'",
    )


def get(url: str, header: str) -> dict:
    return http.get_json(url, header, AUTH_HINT)


def extract_attachment_urls_from_html(html: str) -> list[str]:
    """
    Pull /_apis/wit/attachments/... URLs out of inline HTML.

    Covers both <img src="…"> (pasted images) and <a href="…"> (file links),
    the two ways ADO embeds an attachment inside description or comment HTML.
    """
    return re.findall(r'(?:src|href)="([^"]*/_apis/wit/attachments/[^"]*)"', html)


def attachment_guid_from_url(url: str) -> str:
    """The attachment GUID — the last path segment of an ADO attachment URL."""
    return urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]


def original_name_from_url(url: str) -> str:
    """
    Read the original filename ADO carries in the fileName query parameter.

    Inline attachment URLs always carry it; it is absent from the plain
    relation URL form, where the name comes from the relation attributes.
    """
    query = urllib.parse.urlparse(url).query
    return urllib.parse.parse_qs(query).get("fileName", [""])[0]


def safe_filename(name: str) -> str:
    """Strip characters that are illegal in Windows/Linux filenames."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def local_filename_for(url: str, display_name: str) -> str:
    """
    The on-disk filename for an attachment: its GUID plus the original extension.

    ADO names every pasted screenshot "image.png", so original names collide
    constantly. Keying the file on the attachment GUID makes it unique by
    construction and stable across runs — the same attachment always lands on
    the same filename, so a digest written earlier keeps pointing at the right
    file even if images are later added or reordered. The extension is kept so
    file-type detection still works, and the original name stays in the
    attachment's "name" field for display.
    """
    guid = safe_filename(attachment_guid_from_url(url))
    if not guid:
        return safe_filename(display_name) or "attachment"
    return f"{guid}{safe_filename(Path(display_name).suffix)}"


def extract_inline_attachments(
    html: str, source: str, comment_id: int | None
) -> list[dict]:
    """Build attachment records for every attachment URL embedded in HTML."""
    return [
        {
            "source": source,
            "name": original_name_from_url(url) or attachment_guid_from_url(url),
            "url": url,
            "comment_id": comment_id,
        }
        for url in extract_attachment_urls_from_html(html)
    ]


def wi_id_from_url(url: str) -> int | None:
    match = re.search(r"/workItems/(\d+)$", url)
    return int(match.group(1)) if match else None


def fetch_work_item_recursive(
    wi_id: int,
    header: str,
    org: str,
    project_encoded: str,
    visited: set[int],
    depth: int,
    allowed_relations: frozenset[str],
) -> dict:
    indent = "  " * depth
    print(f"{indent}Fetching work item {wi_id} (depth {depth})…")

    visited.add(wi_id)

    try:
        work_item = get(
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{wi_id}"
            f"?$expand=all&api-version={API_VERSION}",
            header,
        )
    except NETWORK_ERRORS as exc:
        print(
            f"{indent}  Warning: could not fetch work item {wi_id} → {exc}",
            file=sys.stderr,
        )
        return {"id": wi_id, "error": str(exc), "skipped_reason": "fetch_failed"}

    try:
        comments_data: dict = get(
            f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
            f"/{wi_id}/comments?api-version={COMMENTS_API_VERSION}",
            header,
        )
    except NETWORK_ERRORS as exc:
        print(
            f"{indent}  Warning: could not fetch comments for {wi_id} → {exc}",
            file=sys.stderr,
        )
        comments_data = {"count": 0, "comments": []}

    attachments: list[dict] = []
    for rel in work_item.get("relations") or []:
        if rel.get("rel") == "AttachedFile":
            attachments.append(
                {
                    "source": "relation",
                    "name": rel.get("attributes", {}).get("name", ""),
                    "url": rel.get("url", ""),
                    "comment_id": None,
                }
            )
    # An image pasted into a description or acceptance criteria is embedded as
    # inline HTML and is NOT exposed as an AttachedFile relation, so every HTML
    # field has to be scanned directly or those attachments are missed.
    for field_name, value in (work_item.get("fields") or {}).items():
        if isinstance(value, str):
            attachments.extend(
                extract_inline_attachments(
                    value, f"field_inline:{field_name}", comment_id=None
                )
            )
    for comment in comments_data.get("comments") or []:
        attachments.extend(
            extract_inline_attachments(
                comment.get("text") or "",
                "comment_inline_image",
                comment_id=comment.get("id"),
            )
        )

    related: list[dict] = []
    for rel in work_item.get("relations") or []:
        rel_type = rel.get("rel", "")
        if rel_type not in RELATION_TYPES:
            continue

        related_id = wi_id_from_url(rel.get("url", ""))
        if related_id is None:
            continue

        relation_label = RELATION_TYPES[rel_type]

        if relation_label not in allowed_relations:
            print(
                f"{indent}  Skipping {relation_label} #{related_id} "
                "(not in traversal policy)"
            )
            related.append(
                {
                    "relation_type": relation_label,
                    "id": related_id,
                    "skipped_reason": "traversal_policy",
                }
            )
            continue

        if related_id in visited:
            print(
                f"{indent}  Skipping {relation_label} #{related_id} (already visited)"
            )
            related.append(
                {
                    "relation_type": relation_label,
                    "id": related_id,
                    "skipped_reason": "already_visited",
                }
            )
            continue

        if depth >= MAX_DEPTH:
            print(
                f"{indent}  Skipping {relation_label} #{related_id} "
                f"(max depth {MAX_DEPTH} reached)"
            )
            related.append(
                {
                    "relation_type": relation_label,
                    "id": related_id,
                    "skipped_reason": "max_depth_reached",
                }
            )
            continue

        node = fetch_work_item_recursive(
            related_id,
            header,
            org,
            project_encoded,
            visited,
            depth + 1,
            allowed_relations,
        )
        related.append({"relation_type": relation_label, **node})

    return {
        "id": wi_id,
        "work_item": work_item,
        "discussion": comments_data,
        "attachments": attachments,
        "related": related,
    }


def collect_all_attachments(node: dict) -> list[dict]:
    """Recursively gather every attachment entry from the tree."""
    attachments = list(node.get("attachments") or [])
    for child in node.get("related") or []:
        attachments.extend(collect_all_attachments(child))
    return attachments


def run(ticket_id: str, org: str, project: str, header: str) -> dict:
    work_item_id = int(ticket_id)
    project_encoded = urllib.parse.quote(project, safe="")

    out_dir = paths.ticket_dir("ado", ticket_id) / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        root_wi = get(
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{work_item_id}"
            f"?fields=System.WorkItemType&api-version={API_VERSION}",
            header,
        )
        root_type = (root_wi.get("fields") or {}).get("System.WorkItemType", "").lower()
    except NETWORK_ERRORS as exc:
        print(f"Warning: could not determine work item type — {exc}", file=sys.stderr)
        root_type = ""

    if root_type == "task":
        allowed_relations = TASK_RELATIONS
        print("Work item type: Task — traversal limited to parent only")
    else:
        allowed_relations = FULL_RELATIONS
        print(f"Work item type: {root_type.title() or 'Unknown'} — full traversal")

    visited: set[int] = set()
    tree = fetch_work_item_recursive(
        work_item_id,
        header,
        org,
        project_encoded,
        visited,
        depth=0,
        allowed_relations=allowed_relations,
    )

    all_attachments = collect_all_attachments(tree)

    # One attachment can surface from several sources: an AttachedFile relation
    # and an inline reference in a field carry different URLs for the same
    # file, so dedupe on the attachment GUID rather than on the URL.
    unique: dict[str, dict] = {}
    for att in all_attachments:
        unique.setdefault(attachment_guid_from_url(att["url"]), att)

    targets = {
        guid: out_dir / local_filename_for(att["url"], att["name"])
        for guid, att in unique.items()
    }
    kept_count = sum(1 for dest in targets.values() if dest.exists())
    print(
        f"\nAttachments: {kept_count} kept from previous fetch, "
        f"{len(unique) - kept_count} new to download…"
    )

    downloaded: dict[str, dict] = {}
    for guid, att in unique.items():
        dest = targets[guid]

        # Naming is deterministic, so an existing file is this same attachment.
        if dest.exists():
            downloaded[guid] = {"local_filename": dest.name, "download_ok": True}
            continue

        print(f"  Downloading {dest.name}…")
        ok, error = http.download(att["url"], header, dest, AUTH_HINT)
        if not ok:
            print(f"  Warning: could not download {att['url']} → {error}", file=sys.stderr)
        if ok and zipfile.is_zipfile(dest):
            extract_dir = dest.parent / dest.stem
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(extract_dir)
            print(f"    Extracted to {extract_dir.name}/")
        downloaded[guid] = {
            "local_filename": dest.name if ok else None,
            "download_ok": ok,
        }

    def annotate(node: dict) -> None:
        for att in node.get("attachments") or []:
            att.update(downloaded.get(attachment_guid_from_url(att["url"]), {}))
        for child in node.get("related") or []:
            annotate(child)

    annotate(tree)

    raw = {
        "meta": {
            "organization": org,
            "project": project,
            "work_item_id": work_item_id,
            "max_depth": MAX_DEPTH,
            "total_work_items_fetched": len(visited),
        },
        "tree": tree,
    }

    json_path = out_dir / "raw.json"
    json_path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    fields = (tree.get("work_item") or {}).get("fields") or {}
    canonical_type, native_type, type_note = resolve_type(fields)

    tickets.update(
        "ado",
        ticket_id,
        title=fields.get("System.Title"),
        state=fields.get("System.State"),
        type=canonical_type,
        native_type=native_type,
        url=f"https://dev.azure.com/{org}/{urllib.parse.quote(project)}"
        f"/_workitems/edit/{work_item_id}",
        last_fetched_at=tickets.now_iso(),
        fingerprint={"rev": (tree.get("work_item") or {}).get("rev")},
    )

    print(f"\nOutput directory: {out_dir}")

    return {
        "raw_json": str(json_path),
        "work_items_fetched": len(visited),
        "attachments_kept": kept_count,
        "attachments_downloaded": len(unique) - kept_count,
        "attachments_failed": [
            att["name"]
            for guid, att in unique.items()
            if not downloaded.get(guid, {}).get("download_ok")
        ],
        "type": canonical_type,
        "native_type": native_type,
        "type_note": type_note,
    }
