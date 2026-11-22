"""
Mirror an Azure DevOps work item through the `az` CLI, which holds the
credentials: no token is read, printed or stored here.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from sdlclib.errors import SdlcError

AZ_HINT = "Install the Azure CLI and run `az login`, then try again."

# The audience a token must be issued for to be accepted by dev.azure.com.
RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"

API_VERSION = "7.1"
BATCH_SIZE = 200  # the most work item ids one request accepts
COMMENTS_API_VERSION = "7.1-preview.4"


def az_rest(url: str, params: list[str], api_version: str, output: Path) -> None:
    executable = shutil.which("az")
    if not executable:
        raise SdlcError("the Azure CLI ('az') was not found on PATH", hint=AZ_HINT)
    # Parameters travel as their own arguments: an `&` inside the URL would be
    # read as a command separator by the cmd.exe that runs the `az` shim on Windows.
    command = [
        executable,
        "rest",
        "--resource",
        RESOURCE,
        "--method",
        "get",
        "--url",
        url,
        "--output-file",
        str(output),
        "--url-parameters",
        *params,
        f"api-version={api_version}",
    ]
    result = subprocess.run(command, capture_output=True, timeout=120, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise SdlcError(f"`az rest` for {url} failed: {detail}")


def get_json(url: str, params: list[str] | None = None, api_version: str = API_VERSION) -> dict:
    # `az` writes to a file because the console codepage it prints in on
    # Windows would turn any non-ASCII character in a ticket into mojibake.
    with tempfile.TemporaryDirectory() as scratch:
        output = Path(scratch) / "response.json"
        az_rest(url, params or [], api_version, output)
        return json.loads(output.read_text(encoding="utf-8"))


RELATION_LABELS = {
    "System.LinkTypes.Hierarchy-Reverse": "parent",
    "System.LinkTypes.Hierarchy-Forward": "children",
    "System.LinkTypes.Dependency-Reverse": "predecessors",
    "System.LinkTypes.Dependency-Forward": "successors",
    "System.LinkTypes.Related": "related",
}
SUMMARY_FIELDS = {
    "title": "System.Title",
    "state": "System.State",
    "type": "System.WorkItemType",
}


def related_id(url: str) -> int | None:
    match = re.search(r"/workItems/(\d+)$", url, re.IGNORECASE)
    return int(match.group(1)) if match else None


def summaries(organization_url: str, ids: list[int]) -> dict[int, dict]:
    """Title, state and type of each id, one level deep; what the account cannot read stays empty."""
    found: dict[int, dict] = {}
    for start in range(0, len(ids), BATCH_SIZE):
        batch = ids[start : start + BATCH_SIZE]
        answer = get_json(
            f"{organization_url}/_apis/wit/workitems",
            [
                f"ids={','.join(map(str, batch))}",
                f"fields={','.join(SUMMARY_FIELDS.values())}",
                "errorPolicy=Omit",
            ],
        )
        for item in answer["value"]:
            if item:
                found[item["id"]] = {
                    key: item["fields"].get(field)
                    for key, field in SUMMARY_FIELDS.items()
                }
    return found


def group_relations(organization_url: str, relations: list[dict]) -> dict:
    grouped: dict = {
        "parent": None,
        "children": [],
        "predecessors": [],
        "successors": [],
        "related": [],
        "hyperlinks": [],
        "other": [],
    }
    linked = [
        (RELATION_LABELS[relation["rel"]], related_id(relation["url"]))
        for relation in relations
        if relation["rel"] in RELATION_LABELS
    ]
    details = summaries(
        organization_url, sorted({number for _, number in linked if number})
    )
    empty = dict.fromkeys(SUMMARY_FIELDS)
    for relation in relations:
        label = RELATION_LABELS.get(relation["rel"])
        if label:
            number = related_id(relation["url"])
            entry = {"id": number, **details.get(number, empty)}
            if label == "parent":
                grouped["parent"] = entry
            else:
                grouped[label].append(entry)
        elif relation["rel"] == "Hyperlink":
            grouped["hyperlinks"].append(
                {
                    "url": relation["url"],
                    "comment": relation.get("attributes", {}).get("comment"),
                }
            )
        elif relation["rel"] != "AttachedFile":
            grouped["other"].append(relation)
    return grouped


def discover_coordinates(ticket_id: str, known: dict) -> dict:
    """An id names no project; the work item does, and asking an organization-level URL needs none."""
    item = get_json(
        f"https://dev.azure.com/{known['organization']}/_apis/wit/workItems/{ticket_id}",
        ["fields=System.TeamProject"],
    )
    return {"organization": known["organization"], "project": item["fields"]["System.TeamProject"]}


def fetch(ticket_id: str, coordinates: dict, raw_dir: Path) -> dict:
    organization = coordinates["organization"]
    project = coordinates["project"]
    organization_url = f"https://dev.azure.com/{organization}"

    work_item = get_json(
        f"{organization_url}/_apis/wit/workItems/{ticket_id}", ["$expand=all"]
    )
    comments = get_json(
        f"{organization_url}/{quote(project, safe='')}/_apis/wit/workItems/{ticket_id}/comments",
        api_version=COMMENTS_API_VERSION,
    )["comments"]

    relations = group_relations(organization_url, work_item.get("relations") or [])

    raw = {
        "meta": {
            "organization": organization,
            "project": project,
            "work_item_id": int(ticket_id),
        },
        "work_item": work_item,
        "comments": comments,
        "relations": relations,
    }
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "raw.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    fields = work_item["fields"]
    return {
        "title": fields["System.Title"],
        "state": fields["System.State"],
        "url": f"{organization_url}/{quote(fields['System.TeamProject'], safe='')}"
        f"/_workitems/edit/{ticket_id}",
        "fingerprint": {"rev": work_item["rev"]},
        "report": {
            "raw_json": str(raw_dir / "raw.json"),
            "comments": len(comments),
            "relations": {
                label: (len(found) if isinstance(found, list) else found is not None)
                for label, found in relations.items()
            },
        },
    }
