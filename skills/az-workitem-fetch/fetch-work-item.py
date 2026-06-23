#!/usr/bin/env python3
"""
Fetches a complete Azure DevOps work item by ID and dumps all raw data
(work item fields, comments, relations, attachments) into a structured JSON
file plus downloaded attachment files under .claude/.az-workitems/{id}/raw/.

Related work items (parent, children, siblings) are fetched recursively up to
MAX_DEPTH levels deep. Already-visited IDs are tracked to prevent cycles.

Re-fetch behavior:
  - raw.json is always re-downloaded.
  - Attachment files already present on disk are kept and NOT re-downloaded.
  - New attachments (URLs not previously seen) are downloaded normally.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

MAX_DEPTH = 3

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
        req = urllib.request.Request(url, headers={"Authorization": make_auth_header(pat)})
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:
        print(f"  Warning: could not download {url} → {exc}", file=sys.stderr)
        return False


def extract_attachment_urls_from_html(html: str) -> list[str]:
    """Pull /_apis/wit/attachments/... URLs from inline <img> src attributes."""
    return re.findall(r'src="([^"]*/_apis/wit/attachments/[^"]*)"', html)


def safe_filename(name: str) -> str:
    """Strip characters that are illegal in Windows/Linux filenames."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def find_claude_dir(start: Path) -> Path:
    """
    Walk upward looking for an existing .claude directory.
    Falls back to creating one in start.
    """
    current = start.resolve()
    while True:
        candidate = current / ".claude"
        if candidate.is_dir():
            return candidate
        for sibling in current.parent.iterdir():
            if sibling.is_dir() and sibling.name == ".claude" and sibling != current:
                return sibling
        parent = current.parent
        if parent == current:
            local = start / ".claude"
            local.mkdir(parents=True, exist_ok=True)
            return local
        current = parent


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
    except Exception as exc:
        print(f"{indent}  Warning: could not fetch work item {wi_id} → {exc}", file=sys.stderr)
        return {"id": wi_id, "error": str(exc), "skipped_reason": "fetch_failed"}

    # Fetch discussion comments
    comments_url = (
        f"https://dev.azure.com/{org}/{project_encoded}/_apis/wit/workItems"
        f"/{wi_id}/comments?api-version=7.1-preview.4"
    )
    try:
        comments_data = get(comments_url, pat)
    except Exception as exc:
        print(f"{indent}  Warning: could not fetch comments for {wi_id} → {exc}", file=sys.stderr)
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
    for comment in (comments_data.get("comments") or []):
        comment_html = comment.get("text") or ""
        for img_url in extract_attachment_urls_from_html(comment_html):
            guid_match = re.search(r"attachments/([^?/]+)", img_url)
            fname = guid_match.group(1) + ".png" if guid_match else "inline-image.png"
            attachments.append(
                {
                    "source": "comment_inline_image",
                    "name": fname,
                    "url": img_url,
                    "comment_id": comment.get("id"),
                }
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
            print(f"{indent}  Skipping {relation_label} #{related_id} (not in traversal policy)")
            related.append(
                {
                    "relation_type": relation_label,
                    "id": related_id,
                    "skipped_reason": "traversal_policy",
                }
            )
            continue

        if related_id in visited:
            print(f"{indent}  Skipping {relation_label} #{related_id} (already visited)")
            related.append(
                {
                    "relation_type": relation_label,
                    "id": related_id,
                    "skipped_reason": "already_visited",
                }
            )
            continue

        if depth >= MAX_DEPTH:
            print(f"{indent}  Skipping {relation_label} #{related_id} (max depth {MAX_DEPTH} reached)")
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


def load_existing_url_map(out_dir: Path) -> dict[str, str]:
    """
    Read the existing raw.json (if present) and return a mapping of
    attachment URL → local_filename for files that were already downloaded.
    """
    raw_json = out_dir / "raw.json"
    if not raw_json.exists():
        return {}

    try:
        data = json.loads(raw_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    url_map: dict[str, str] = {}

    def walk(node: dict) -> None:
        for att in node.get("attachments") or []:
            if att.get("download_ok") and att.get("local_filename"):
                url_map[att["url"]] = att["local_filename"]
        for child in node.get("related") or []:
            walk(child)

    walk(data.get("tree") or {})
    return url_map


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch an Azure DevOps work item and dump raw data to disk."
    )
    parser.add_argument("--id", required=True, type=int, help="Work item ID")
    parser.add_argument("--pat", required=True, help="Azure DevOps Personal Access Token")
    parser.add_argument("--org", required=True, help="ADO organization name (e.g. mycompany)")
    parser.add_argument("--project", required=True, help="ADO project name")
    args = parser.parse_args()

    work_item_id: int = args.id
    pat: str = args.pat
    org: str = args.org
    project: str = args.project
    project_encoded: str = urllib.parse.quote(project, safe="")

    cwd = Path.cwd()
    claude_dir = find_claude_dir(cwd)
    wi_dir = claude_dir / ".az-workitems" / str(work_item_id)
    out_dir = wi_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Remember which attachments were already downloaded before this run
    existing_url_map = load_existing_url_map(out_dir)

    # Determine traversal policy from the root work item type
    try:
        root_wi = get(
            f"https://dev.azure.com/{org}/_apis/wit/workItems/{work_item_id}"
            f"?fields=System.WorkItemType&api-version=7.1",
            pat,
        )
        root_type = (root_wi.get("fields") or {}).get("System.WorkItemType", "").lower()
    except Exception as exc:
        print(f"Warning: could not determine work item type — {exc}", file=sys.stderr)
        root_type = ""

    if root_type == "task":
        # Tasks: fetch the task itself and its parent only
        allowed_relations: frozenset[str] = frozenset({"parent"})
        print(f"Work item type: Task — traversal limited to parent only")
    else:
        # User Story, Bug, and anything else: full traversal
        allowed_relations = frozenset({"parent", "child", "related"})
        print(f"Work item type: {root_type.title() or 'Unknown'} — full traversal")

    # Recursively fetch the entire work item tree (always fresh)
    visited: set[int] = set()
    tree = fetch_work_item_recursive(
        work_item_id, pat, org, project_encoded, visited, depth=0,
        allowed_relations=allowed_relations,
    )

    # Download attachments — skip files already present on disk
    all_attachments = collect_all_attachments(tree)
    new_count = sum(1 for a in all_attachments if a["url"] not in existing_url_map)
    kept_count = len(all_attachments) - new_count
    print(f"\nAttachments: {kept_count} kept from previous fetch, {new_count} new to download…")

    downloaded: dict[str, dict] = {}  # url → download result, deduped by URL

    for att in all_attachments:
        url = att["url"]
        if url in downloaded:
            continue

        # Reuse existing file if already downloaded
        if url in existing_url_map:
            existing_fname = existing_url_map[url]
            existing_path = out_dir / existing_fname
            if existing_path.exists():
                downloaded[url] = {"local_filename": existing_fname, "download_ok": True}
                continue
            # File was recorded but missing from disk — re-download it

        raw_name = att["name"] or "attachment"
        fname = safe_filename(raw_name)
        dest = out_dir / fname
        counter = 1
        while dest.exists():
            stem, suffix = os.path.splitext(fname)
            dest = out_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        print(f"  Downloading {fname}…")
        ok = download_file(url, pat, dest)
        if ok and zipfile.is_zipfile(dest):
            extract_dir = dest.parent / dest.stem
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(extract_dir)
            print(f"    Extracted to {extract_dir.name}/")
        downloaded[url] = {
            "local_filename": dest.name if ok else None,
            "download_ok": ok,
        }

    # Annotate every attachment node in the tree with its download result
    def annotate(node: dict) -> None:
        for att in node.get("attachments") or []:
            result = downloaded.get(att["url"], {})
            att.update(result)
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
    json_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nOutput directory: {out_dir}")


if __name__ == "__main__":
    main()
