#!/usr/bin/env python3
"""
Fetches a complete Azure DevOps work item by ID and dumps all raw data
(work item fields, comments, relations, attachments) into a structured JSON
file plus downloaded attachment files under ~/.az-workitems/{id}/raw/.

Related work items (parent, children, siblings) are fetched recursively up to
MAX_DEPTH levels deep. Already-visited IDs are tracked to prevent cycles.

Attachment naming:
  - Files are named after their ADO attachment GUID plus the original
    extension, because ADO names every pasted screenshot "image.png".

Re-fetch behavior:
  - raw.json is always re-downloaded.
  - Naming is deterministic, so a file already on disk is the same attachment
    and is kept, NOT re-downloaded.
  - New attachments are downloaded normally.
"""

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

MAX_DEPTH = 3

# Failures raised while fetching/downloading over the network or decoding a
# response. Caught so a single bad relation doesn't abort the whole tree.
NETWORK_ERRORS = (urllib.error.URLError, json.JSONDecodeError, OSError)

RELATION_TYPES = {
    "System.LinkTypes.Hierarchy-Reverse": "parent",
    "System.LinkTypes.Hierarchy-Forward": "child",
    "System.LinkTypes.Related": "related",
}


def make_auth_header(pat: str) -> str:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return f"Basic {token}"


def get(url: str, pat: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": make_auth_header(pat)})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def download_file(url: str, pat: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(
            url, headers={"Authorization": make_auth_header(pat)}
        )
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"  Warning: could not download {url} → {exc}", file=sys.stderr)
        return False


def extract_attachment_urls_from_html(html: str) -> list[str]:
    """
    Pull /_apis/wit/attachments/... URLs out of inline HTML.

    Covers both <img src="…"> (pasted images) and <a href="…"> (file links),
    the two ways ADO embeds an attachment inside description or comment HTML.
    """
    return re.findall(r'(?:src|href)="([^"]*/_apis/wit/attachments/[^"]*)"', html)


def attachment_guid_from_url(url: str) -> str:
    """Extract the attachment GUID — the last path segment of an ADO attachment URL."""
    return urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]


def original_name_from_url(url: str) -> str:
    """
    Read the original filename ADO carries in the fileName query parameter.

    Inline attachment URLs always carry it; it is absent from the plain
    relation URL form, where the name comes from the relation attributes.
    """
    query = urllib.parse.urlparse(url).query
    return urllib.parse.parse_qs(query).get("fileName", [""])[0]


def local_filename_for(url: str, display_name: str) -> str:
    """
    Build the on-disk filename for an attachment: its GUID plus the original
    extension.

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


def safe_filename(name: str) -> str:
    """Strip characters that are illegal in Windows/Linux filenames."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def wi_id_from_url(url: str) -> int | None:
    """Extract the numeric work item ID from a relation URL."""
    match = re.search(r"/workItems/(\d+)$", url)
    return int(match.group(1)) if match else None


def fetch_work_item_recursive(
    wi_id: int,
    pat: str,
    org: str,
    project_encoded: str,
    visited: set[int],
    depth: int,
    allowed_relations: frozenset[str],
) -> dict:
    """
    Fetch a work item and its relations up to MAX_DEPTH levels.

    allowed_relations controls which relation types are expanded:
      - User Story / Bug: {"parent", "child", "related"}
      - Task:             {"parent"}  (children and siblings are not expanded)
    """
    indent = "  " * depth
    print(f"{indent}Fetching work item {wi_id} (depth {depth})…")

    visited.add(wi_id)

    # Fetch core work item
    try:
        wi_url = (
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{wi_id}"
            f"?$expand=all&api-version=7.1"
        )
        work_item = get(wi_url, pat)
    except NETWORK_ERRORS as exc:
        print(
            f"{indent}  Warning: could not fetch work item {wi_id} → {exc}",
            file=sys.stderr,
        )
        return {"id": wi_id, "error": str(exc), "skipped_reason": "fetch_failed"}

    # Fetch discussion comments
    comments_url = (
        f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
        f"/{wi_id}/comments?api-version=7.1-preview.4"
    )
    try:
        comments_data: dict = get(comments_url, pat)
    except NETWORK_ERRORS as exc:
        print(
            f"{indent}  Warning: could not fetch comments for {wi_id} → {exc}",
            file=sys.stderr,
        )
        comments_data = {"count": 0, "comments": []}

    # Collect attachment metadata (actual downloads happen in main)
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

    # Resolve related work items recursively
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
                f"{indent}  Skipping {relation_label} #{related_id} (not in traversal policy)"
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
                f"{indent}  Skipping {relation_label} #{related_id} (max depth {MAX_DEPTH} reached)"
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
            related_id, pat, org, project_encoded, visited, depth + 1, allowed_relations
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch an Azure DevOps work item and dump raw data to disk."
    )
    parser.add_argument("--id", required=True, type=int, help="Work item ID")
    parser.add_argument(
        "--pat", required=True, help="Azure DevOps Personal Access Token"
    )
    parser.add_argument(
        "--org", required=True, help="ADO organization name (e.g. mycompany)"
    )
    parser.add_argument("--project", required=True, help="ADO project name")
    args = parser.parse_args()

    work_item_id: int = args.id
    pat: str = args.pat
    org: str = args.org
    project: str = args.project
    project_encoded: str = urllib.parse.quote(project, safe="")

    # Work item data is machine-wide, not per-workspace: Path.home() resolves
    # to %USERPROFILE% on Windows and $HOME on Linux/macOS.
    wi_dir = Path.home() / ".az-workitems" / str(work_item_id)
    out_dir = wi_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine traversal policy from the root work item type
    try:
        root_wi = get(
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{work_item_id}"
            f"?fields=System.WorkItemType&api-version=7.1",
            pat,
        )
        root_type = (root_wi.get("fields") or {}).get("System.WorkItemType", "").lower()
    except NETWORK_ERRORS as exc:
        print(f"Warning: could not determine work item type — {exc}", file=sys.stderr)
        root_type = ""

    if root_type == "task":
        # Tasks: fetch the task itself and its parent only
        allowed_relations: frozenset[str] = frozenset({"parent"})
        print("Work item type: Task — traversal limited to parent only")
    else:
        # User Story, Bug, and anything else: full traversal
        allowed_relations = frozenset({"parent", "child", "related"})
        print(f"Work item type: {root_type.title() or 'Unknown'} — full traversal")

    # Recursively fetch the entire work item tree (always fresh)
    visited: set[int] = set()
    tree = fetch_work_item_recursive(
        work_item_id,
        pat,
        org,
        project_encoded,
        visited,
        depth=0,
        allowed_relations=allowed_relations,
    )

    # Download attachments — skip files already present on disk
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

    downloaded: dict[str, dict] = {}  # guid → download result
    for guid, att in unique.items():
        dest = targets[guid]

        # Naming is deterministic, so an existing file is this same attachment.
        if dest.exists():
            downloaded[guid] = {"local_filename": dest.name, "download_ok": True}
            continue

        print(f"  Downloading {dest.name}…")
        ok = download_file(att["url"], pat, dest)
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

    # Annotate every attachment node in the tree with its download result
    def annotate(node: dict) -> None:
        for att in node.get("attachments") or []:
            att.update(downloaded.get(attachment_guid_from_url(att["url"]), {}))
        for child in node.get("related") or []:
            annotate(child)

    annotate(tree)

    # Write master raw JSON (always overwritten)
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

    print(f"\nOutput directory: {out_dir}")


if __name__ == "__main__":
    main()
