"""
Mirror an Azure DevOps work item through the `az` CLI, which holds the
credentials: no token is read, printed or stored here.
"""

import html
import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from sdlclib import journal, process
from sdlclib.errors import EXIT_NOT_FOUND, SdlcError

AZ_HINT = "Install the Azure CLI and run `az login`, then try again."
# What `az` prints when the sign-in, not the request, is what failed.
SIGN_IN_MARKERS = ("AADSTS", "az login", "Unauthorized")
NOT_FOUND_MARKERS = ("TF401232", "Not Found", "404")

# The audience a token must be issued for to be accepted by dev.azure.com.
RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
SIGN_IN_HINT = f"Sign in with `az login --scope {RESOURCE}/.default`, then try again."

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
    result = process.run(command)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        if any(marker in detail for marker in SIGN_IN_MARKERS):
            raise SdlcError(
                f"Azure DevOps rejected the sign-in: {detail}", hint=SIGN_IN_HINT
            )
        code = EXIT_NOT_FOUND if any(m in detail for m in NOT_FOUND_MARKERS) else 1
        raise SdlcError(f"`az rest` for {url} failed: {detail}", code)


def get_json(
    url: str, params: list[str] | None = None, api_version: str = API_VERSION
) -> dict:
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


def all_comments(organization_url: str, project: str, ticket_id: str) -> list[dict]:
    url = f"{organization_url}/{quote(project, safe='')}/_apis/wit/workItems/{ticket_id}/comments"
    comments: list[dict] = []
    params: list[str] = []
    while True:
        page = get_json(url, params, COMMENTS_API_VERSION)
        comments += page["comments"]
        token = page.get("continuationToken")
        if not token:
            return comments
        params = [f"continuationToken={token}"]


ATTACHMENT_URL = re.compile(r"https?://[^\s\"'<>)]*/_apis/wit/attachments/[^\s\"'<>)]*")


def attachment_guid(url: str) -> str:
    return urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]


def belongs_to_organization(url: str, organization: str) -> bool:
    """
    Whether `url` is on the ticket's own organization, the only place `az rest` may be sent.

    `az rest --resource` attaches a bearer token to whatever URL it is given,
    and these URLs come from work item text and comments that anyone with
    access can write. The host is compared exactly after parsing: a prefix or
    a substring test is fooled by `dev.azure.com.evil.example` and by
    `dev.azure.com@evil.example`.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != parsed.hostname:
        return False
    if parsed.hostname == "dev.azure.com":
        first_segment = parsed.path.lstrip("/").partition("/")[0]
        return first_segment.casefold() == organization.casefold()
    return parsed.hostname == f"{organization.casefold()}.visualstudio.com"


def find_attachments(
    work_item: dict, comments: list[dict], organization: str
) -> list[dict]:
    """
    Every attachment the work item references, once per attachment id.

    A pasted image is embedded in a field or comment and is not an
    `AttachedFile` relation, so the text is scanned as well. A relation and
    an embed carry different URLs for one file, hence the id, not the URL.
    A URL outside the organization is recorded with the reason it is not
    downloaded; keyed by the URL, it cannot displace a genuine attachment
    that happens to share its id.
    """
    found: dict[str, dict] = {}

    def record(url: str, name: str, found_in: str) -> None:
        attachment = {"url": url, "name": name, "found_in": found_in}
        key = attachment_guid(url)
        if not belongs_to_organization(url, organization):
            attachment.update(
                local_filename=None,
                error=f"not downloaded: the URL is not on the ticket's organization '{organization}'",
            )
            key = url
        found.setdefault(key, attachment)

    for relation in work_item.get("relations") or []:
        if relation["rel"] == "AttachedFile":
            name = relation.get("attributes", {}).get("name") or attachment_guid(
                relation["url"]
            )
            record(relation["url"], name, "relation")

    texts = [
        (f"field:{name}", value)
        for name, value in work_item["fields"].items()
        if isinstance(value, str)
    ]
    for comment in comments:
        for key in ("text", "renderedText"):
            texts.append((f"comment:{comment['id']}", comment.get(key) or ""))
    for found_in, text in texts:
        for url in ATTACHMENT_URL.findall(text):
            url = html.unescape(url)
            names = parse_qs(urlparse(url).query).get("fileName")
            record(url, names[0] if names else attachment_guid(url), found_in)
    return list(found.values())


def download(attachment: dict, raw_dir: Path) -> str:
    """Returns "kept", "downloaded" or "failed", recording the file name or the error on the attachment."""
    if attachment.get("error"):
        return "failed"
    guid = attachment_guid(attachment["url"])
    # ADO names every pasted screenshot `image.png`, so the id names the file;
    # being deterministic, it is also how a refresh recognises what it already holds.
    suffix = re.sub(r"[^A-Za-z0-9.]", "", Path(attachment["name"]).suffix)
    destination = raw_dir / f"{guid}{suffix}"
    if destination.exists():
        attachment["local_filename"] = destination.name
        return "kept"
    try:
        # The query is dropped: an attachment is addressed by its id, and `fileName` only names it.
        az_rest(attachment["url"].partition("?")[0], [], API_VERSION, destination)
    except SdlcError as error:
        destination.unlink(missing_ok=True)
        attachment.update(local_filename=None, error=str(error))
        return "failed"
    attachment["local_filename"] = destination.name
    return "downloaded"


def discover_coordinates(ticket_id: str, known: dict) -> dict:
    """An id names no project; the work item does, and asking an organization-level URL needs none."""
    item = get_json(
        f"https://dev.azure.com/{known['organization']}/_apis/wit/workItems/{ticket_id}",
        ["fields=System.TeamProject"],
    )
    return {
        "organization": known["organization"],
        "project": item["fields"]["System.TeamProject"],
    }


def comments_of(raw: dict) -> list[journal.Comment]:
    return [
        journal.Comment(
            text=comment.get("text") or "",
            author=(comment.get("createdBy") or {}).get("displayName"),
        )
        for comment in raw["comments"]
    ]


# Fields Azure DevOps moves on every revision, a comment's included; they say
# that something changed, never what.
REVISION_FIELDS = frozenset(
    {
        "System.Rev",
        "System.ChangedDate",
        "System.ChangedBy",
        "System.AuthorizedDate",
        "System.AuthorizedAs",
        "System.RevisedDate",
        "System.Watermark",
        "System.PersonId",
        "System.CommentCount",
        "System.History",
    }
)


def signature(raw: dict) -> dict:
    """The work item's content without its journal entries or revision bookkeeping, so a post alone does not read as a change."""
    work_item = raw["work_item"]
    return {
        "fields": {
            name: value
            for name, value in work_item["fields"].items()
            if name not in REVISION_FIELDS
        },
        "relations": sorted(
            (relation["rel"], relation["url"])
            for relation in work_item.get("relations") or []
        ),
        "comments": [
            (comment["id"], comment.get("text") or "")
            for comment in journal.without_entries(raw["comments"], comments_of(raw))
        ],
    }


def check(ticket_id: str, coordinates: dict, mirror: dict) -> dict:
    """
    The live revision, in the shape `fetch` records; nothing is downloaded or written.

    A probe that returns no content answers an unmoved revision. Only a moved
    one reads the work item and its comments, to tell a journal post apart.
    """
    organization_url = f"https://dev.azure.com/{coordinates['organization']}"
    item_url = f"{organization_url}/_apis/wit/workItems/{ticket_id}"
    rev = get_json(item_url, ["fields=System.Rev"])["rev"]
    if rev == mirror["work_item"]["rev"]:
        return {"fingerprint": {"rev": rev}}
    upstream = {
        "work_item": get_json(item_url, ["$expand=all"]),
        "comments": all_comments(organization_url, coordinates["project"], ticket_id),
    }
    return {"fingerprint": {"rev": rev}, "upstream": upstream}


def fetch(ticket_id: str, coordinates: dict, raw_dir: Path) -> dict:
    organization = coordinates["organization"]
    project = coordinates["project"]
    organization_url = f"https://dev.azure.com/{organization}"

    work_item = get_json(
        f"{organization_url}/_apis/wit/workItems/{ticket_id}", ["$expand=all"]
    )
    comments = all_comments(organization_url, project, ticket_id)

    relations = group_relations(organization_url, work_item.get("relations") or [])

    attachments = find_attachments(work_item, comments, organization)
    raw_dir.mkdir(parents=True, exist_ok=True)
    outcomes = [download(attachment, raw_dir) for attachment in attachments]

    raw = {
        "meta": {
            "organization": organization,
            "project": project,
            "work_item_id": int(ticket_id),
        },
        "work_item": work_item,
        "comments": comments,
        "relations": relations,
        "attachments": attachments,
    }
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
        "comments": comments_of(raw),
        "report": {
            "raw_json": str(raw_dir / "raw.json"),
            "comments": len(comments),
            "attachments": {
                "found": len(attachments),
                "downloaded": outcomes.count("downloaded"),
                "kept": outcomes.count("kept"),
                "failed": [
                    {"url": a["url"], "error": a["error"]}
                    for a in attachments
                    if a.get("error")
                ],
            },
            "relations": {
                label: (len(found) if isinstance(found, list) else found is not None)
                for label, found in relations.items()
            },
        },
    }
