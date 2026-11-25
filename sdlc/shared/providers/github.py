"""
Mirror a GitHub issue through the `gh` CLI, which holds the credentials: no
token is read, printed or stored here.
"""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from sdlclib import journal, layout, process
from sdlclib.errors import EXIT_NOT_FOUND, SdlcError
from sdlclib.pulls import Line

GH_HINT = "Install the GitHub CLI and run `gh auth login`, then try again."


def gh(args: list[str]) -> subprocess.CompletedProcess:
    executable = shutil.which("gh")
    if not executable:
        raise SdlcError("the GitHub CLI ('gh') was not found on PATH", hint=GH_HINT)
    return process.run([executable, *args])


NOT_FOUND = "404"
SIGNED_OUT_MARKERS = ("HTTP 401", "gh auth login")


def failure_of(result: subprocess.CompletedProcess) -> str:
    return (result.stderr or result.stdout).decode("utf-8", "replace").strip()


def require_auth() -> None:
    result = gh(["auth", "status"])
    if result.returncode != 0:
        raise SdlcError(f"not signed in to GitHub: {failure_of(result)}", hint=GH_HINT)


def gh_json(args: list[str]) -> Any:
    """
    The decoded JSON a `gh` call prints, named in an error by its first two arguments.

    A 404 raises with `EXIT_NOT_FOUND`, and a rejected sign-in with the hint to sign in.
    """
    result = gh(args)
    # A 404 or a rejected sign-in is an answer, and asking again gets the same one.
    answered = (NOT_FOUND, *SIGNED_OUT_MARKERS)
    if result.returncode != 0 and not any(m in failure_of(result) for m in answered):
        # GitHub drops connections now and then; one more try is cheaper than a failed call.
        result = gh(args)
    if result.returncode != 0:
        detail = failure_of(result)
        signed_out = any(marker in detail for marker in SIGNED_OUT_MARKERS)
        raise SdlcError(
            f"`gh {' '.join(args[:2])}` failed: {detail}",
            EXIT_NOT_FOUND if NOT_FOUND in detail else 1,
            hint=GH_HINT if signed_out else "",
        )
    return json.loads(result.stdout)


def api(path: str, paginate: bool = False) -> Any:
    """The decoded JSON of a `gh api` call: an object, or with `paginate` the list of every page's items."""
    args = ["api", path, "-H", "Accept: application/vnd.github+json"]
    if paginate:
        args += ["--paginate", "--slurp"]
    payload = gh_json(args)
    if paginate:
        return [item for page in payload for item in page]
    return payload


URL = re.compile(r"https://[^\s)\]>\"'<]+")
MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\((https://[^)\s]+)")
ASSET = re.compile(r"/user-attachments/assets/([0-9a-f-]{36})")

# Enough to give a download an extension a viewer recognises: an `assets` URL
# carries no file name.
SIGNATURES = (
    (b"\x89PNG", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF8", ".gif"),
    (b"%PDF", ".pdf"),
    (b"PK\x03\x04", ".zip"),
)


def is_attachment(url: str) -> bool:
    parsed = urlparse(url)
    # `gh api` signs a request for the host it is given, so the host must be one
    # of GitHub's own, compared exactly and with no userinfo or port.
    if parsed.scheme != "https" or parsed.netloc != parsed.hostname:
        return False
    if parsed.hostname == "github.com":
        return parsed.path.startswith("/user-attachments/") or bool(
            re.match(r"/[^/]+/[^/]+/files/\d+/", parsed.path)
        )
    return parsed.hostname == "user-images.githubusercontent.com"


def find_attachments(texts: list[tuple[str, str | None]]) -> list[dict]:
    """Every attachment URL in the body and comments, once, with the name its author gave it."""
    found: dict[str, dict] = {}
    for where, text in texts:
        text = text or ""
        names = {url: name for name, url in MARKDOWN_LINK.findall(text)}
        for url in (match.rstrip(".,;:") for match in URL.findall(text)):
            if url in found or not is_attachment(url):
                continue
            name = names.get(url) or unquote(urlparse(url).path.rsplit("/", 1)[-1])
            found[url] = {"url": url, "name": name, "found_in": where}
    return list(found.values())


def local_stem(url: str) -> str:
    """Deterministic, so a refresh recognises what it already downloaded."""
    asset = ASSET.search(urlparse(url).path)
    if asset:
        return asset.group(1)
    tail = unquote(urlparse(url).path).rstrip("/").split("/")[-2:]
    return re.sub(r"[^A-Za-z0-9._-]", "_", "-".join(tail))


def downloaded_file(raw_dir: Path, stem: str) -> Path | None:
    return next(
        (path for path in sorted(raw_dir.glob(f"{stem}*")) if path.is_file()), None
    )


def extension_of(content: bytes) -> str:
    return next((ext for magic, ext in SIGNATURES if content.startswith(magic)), "")


def download(attachment: dict, raw_dir: Path) -> str:
    """Returns "kept", "downloaded" or "failed", recording the file name or the error on the attachment."""
    stem = local_stem(attachment["url"])
    existing = downloaded_file(raw_dir, stem)
    if existing:
        attachment["local_filename"] = existing.name
        return "kept"

    try:
        result = gh(["api", attachment["url"]])
    except SdlcError as error:
        attachment.update(local_filename=None, error=str(error))
        return "failed"
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", "replace").strip() or "empty response"
        attachment.update(local_filename=None, error=detail)
        return "failed"

    name = stem if "." in stem else stem + extension_of(result.stdout)
    (raw_dir / name).write_bytes(result.stdout)
    attachment["local_filename"] = name
    return "downloaded"


def parent_of(base: str) -> dict | None:
    """An issue without a parent answers 404, which is an answer, not a failure."""
    try:
        return api(f"{base}/parent")
    except SdlcError as error:
        if error.code == EXIT_NOT_FOUND:
            return None
        raise


def content(raw: dict, comments: list[dict]) -> dict:
    """What a reader would notice change. `updated_at` is left out on purpose: it moves for activity that changes nothing the mirror holds."""

    def state_of(issues: list[dict]) -> list[tuple]:
        return [(issue["number"], issue["state"]) for issue in issues]

    issue = raw["issue"]
    return {
        "title": issue["title"],
        "body": issue["body"],
        "state": issue["state"],
        "labels": sorted(label["name"] for label in issue["labels"]),
        "comments": [(comment["id"], comment["body"]) for comment in comments],
        "parent": raw["parent"]["number"] if raw["parent"] else None,
        "sub_issues": state_of(raw["sub_issues"]),
        "blocked_by": state_of(raw["blocked_by"]),
        "blocking": state_of(raw["blocking"]),
    }


def fingerprint(raw: dict) -> dict:
    """GitHub has no revision, so the revision is a hash of the issue's content."""
    canonical = json.dumps(
        content(raw, raw["comments"]), sort_keys=True, ensure_ascii=False
    )
    return {"sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}


def signature(raw: dict) -> dict:
    """The issue's content without its journal entries, so a post alone does not read as a change."""
    return content(raw, journal.without_entries(raw["comments"], comments_of(raw)))


HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def split_criteria(body: str) -> tuple[str, str]:
    """
    The body as (description, acceptance criteria).

    GitHub has no criteria field: they are the `Acceptance Criteria` section,
    ending at the next heading of the same or a higher level.
    """
    lines = body.replace("\r\n", "\n").split("\n")
    start: int | None = None
    level = 0
    for index, line in enumerate(lines):
        heading = HEADING.match(line)
        if not heading:
            continue
        depth = len(heading.group(1))
        if start is None and heading.group(2).casefold() == "acceptance criteria":
            start, level = index, depth
        elif start is not None and depth <= level:
            return (
                "\n".join(lines[:start] + lines[index:]),
                "\n".join(lines[start:index]),
            )
    if start is None:
        return body, ""
    return "\n".join(lines[:start]), "\n".join(lines[start:])


def fields(raw: dict) -> dict:
    """The issue's content by the field `sync` names when it changes; journal entries are left out."""
    rest = signature(raw)
    description, criteria = split_criteria(rest.pop("body") or "")
    return {
        "title": rest.pop("title"),
        "state": rest.pop("state"),
        "description": description,
        "acceptance_criteria": criteria,
        **rest,
    }


def read_issue(ticket_id: str, coordinates: dict) -> dict:
    """
    Everything the mirror holds that comes from the issue's own endpoints, written nowhere.

    `fetch` and `check` both read through here, so the fingerprint is computed
    from one shape of data and cannot drift between the two.
    """
    repository = f"{coordinates['owner']}/{coordinates['repository']}"
    base = f"repos/{repository}/issues/{ticket_id}"

    require_auth()
    issue = api(base)
    if "pull_request" in issue:
        raise SdlcError(
            f"{repository}#{ticket_id} is a pull request, not an issue",
            hint="A pull request is not a ticket; fetch the issue it closes instead.",
        )
    return {
        "meta": {"repository": repository, "issue_number": int(ticket_id)},
        "issue": issue,
        "comments": api(f"{base}/comments", paginate=True),
        "parent": parent_of(base),
        "sub_issues": api(f"{base}/sub_issues", paginate=True),
        "blocked_by": api(f"{base}/dependencies/blocked_by", paginate=True),
        "blocking": api(f"{base}/dependencies/blocking", paginate=True),
    }


def comments_of(raw: dict) -> list[journal.Comment]:
    return [
        journal.Comment(
            text=comment["body"], author=(comment.get("user") or {}).get("login")
        )
        for comment in raw["comments"]
    ]


def check(ticket_id: str, coordinates: dict, mirror: dict) -> dict:
    """The live fingerprint and what was read to compute it; nothing is downloaded or written."""
    upstream = read_issue(ticket_id, coordinates)
    return {"fingerprint": fingerprint(upstream), "upstream": upstream}


def fetch(ticket_id: str, coordinates: dict, raw_dir: Path) -> dict:
    raw = read_issue(ticket_id, coordinates)
    issue, comments = raw["issue"], raw["comments"]
    parent, sub_issues = raw["parent"], raw["sub_issues"]
    blocked_by, blocking = raw["blocked_by"], raw["blocking"]

    raw_dir.mkdir(parents=True, exist_ok=True)
    attachments = find_attachments(
        [("body", issue["body"])]
        + [(f"comment:{comment['id']}", comment["body"]) for comment in comments]
    )
    outcomes = [download(attachment, raw_dir) for attachment in attachments]

    raw["attachments"] = attachments
    layout.replace_file(raw_dir / "raw.json", layout.json_bytes(raw))

    return {
        "title": issue["title"],
        "state": issue["state"],
        "url": issue["html_url"],
        "fingerprint": fingerprint(raw),
        "comments": comments_of(raw),
        "report": {
            "raw_json": str(raw_dir / "raw.json"),
            "comments": len(comments),
            "relations": {
                "parent": parent is not None,
                "sub_issues": len(sub_issues),
                "blocked_by": len(blocked_by),
                "blocking": len(blocking),
            },
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
        },
    }


# Pull requests, for `sync`: a repository on GitHub, whatever the ticket's source.

REMOTE = re.compile(
    r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<owner>[^/\s]+)/(?P<repository>[^/\s]+?)(?:\.git)?/?"
)
PULL_URL = re.compile(
    r"https://github\.com/(?P<owner>[^/\s]+)/(?P<repository>[^/\s]+)/pull/(?P<number>\d+)"
)
PULL_FIELDS = "number,url,state,isDraft,reviewDecision,statusCheckRollup"
FAILING = frozenset(
    {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}
)
REVIEWS = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes requested"}


def pull_host(remote_url: str) -> str | None:
    """`{owner}/{repository}` of a GitHub remote; None for any other host."""
    match = REMOTE.fullmatch(remote_url.strip())
    return f"{match['owner']}/{match['repository']}" if match else None


def checks_of(rollup: list[dict]) -> str | None:
    """What a pull request's checks add up to: any failing, any pending, or all passing; None without checks."""
    if not rollup:
        return None
    # A check run reports `status` and `conclusion`; a commit status only `state`.
    outcomes = [item.get("conclusion") or item.get("state") or "" for item in rollup]
    if any(outcome in FAILING for outcome in outcomes):
        return "checks failing"
    pending = any(
        item.get("status", "COMPLETED") != "COMPLETED"
        or outcome in ("", "PENDING", "EXPECTED")
        for item, outcome in zip(rollup, outcomes, strict=True)
    )
    return "checks pending" if pending else "checks passing"


def pull_line(repository: str, pull: dict) -> Line:
    """The record line of a pull request as `gh pr` returns it with `PULL_FIELDS`."""
    status = ["draft"] if pull["isDraft"] else [pull["state"].lower()]
    if status[0] in ("draft", "open"):
        status += [
            part
            for part in (
                checks_of(pull.get("statusCheckRollup") or []),
                REVIEWS.get(pull.get("reviewDecision") or ""),
            )
            if part
        ]
    return Line(
        label=f"{repository}#{pull['number']}",
        url=pull["url"],
        status=", ".join(status),
    )


def pulls_headed_by(repository: str, branch: str) -> list[Line]:
    """The record lines of every pull request, in any state, whose head is `branch`."""
    listed = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--head",
            branch,
            "--state",
            "all",
            "--json",
            PULL_FIELDS,
        ]
    )
    return [pull_line(repository, pull) for pull in listed]


def pull_at(url: str) -> Line | None:
    """The record line of the pull request at `url`; None when it is not a GitHub pull request."""
    match = PULL_URL.fullmatch(url.strip())
    if not match:
        return None
    pull = gh_json(["pr", "view", url, "--json", PULL_FIELDS])
    return pull_line(f"{match['owner']}/{match['repository']}", pull)
