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
from urllib.parse import unquote, urlparse

from sdlclib.errors import EXIT_NOT_FOUND, SdlcError

GH_HINT = "Install the GitHub CLI and run `gh auth login`, then try again."


def gh(args: list[str]) -> subprocess.CompletedProcess:
    executable = shutil.which("gh")
    if not executable:
        raise SdlcError("the GitHub CLI ('gh') was not found on PATH", hint=GH_HINT)
    return subprocess.run(
        [executable, *args], capture_output=True, timeout=120, check=False
    )


def require_auth() -> None:
    result = gh(["auth", "status"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode("utf-8", "replace").strip()
        raise SdlcError(f"not signed in to GitHub: {detail}", hint=GH_HINT)


def api(path: str, paginate: bool = False) -> object:
    args = ["api", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        args += ["--paginate", "--slurp"]
    result = gh(args)
    if result.returncode != 0 and b"404" not in result.stderr:
        # GitHub drops connections now and then; one more try is cheaper than a failed intake.
        result = gh(args)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        code = EXIT_NOT_FOUND if "404" in detail else 1
        raise SdlcError(f"`gh api {path}` failed: {detail}", code)
    payload = json.loads(result.stdout)
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
    if parsed.hostname == "github.com":
        return parsed.path.startswith("/user-attachments/") or bool(
            re.match(r"/[^/]+/[^/]+/files/\d+/", parsed.path)
        )
    return bool(parsed.hostname) and parsed.hostname.endswith(
        "user-images.githubusercontent.com"
    )


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
    except (SdlcError, subprocess.TimeoutExpired) as error:
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


def fingerprint(raw: dict) -> dict:
    """
    GitHub has no revision, so the revision is a hash of what a reader would notice change.

    `updated_at` is left out on purpose: it moves for activity that changes
    nothing the mirror holds, which would make every refresh look stale.
    """

    def state_of(issues: list[dict]) -> list[tuple]:
        return [(issue["number"], issue["state"]) for issue in issues]

    issue = raw["issue"]
    content = {
        "title": issue["title"],
        "body": issue["body"],
        "state": issue["state"],
        "labels": sorted(label["name"] for label in issue["labels"]),
        "comments": [(comment["id"], comment["body"]) for comment in raw["comments"]],
        "parent": raw["parent"]["number"] if raw["parent"] else None,
        "sub_issues": state_of(raw["sub_issues"]),
        "blocked_by": state_of(raw["blocked_by"]),
        "blocking": state_of(raw["blocking"]),
    }
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return {"sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}


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


def check(ticket_id: str, coordinates: dict) -> dict:
    """The live fingerprint, for comparing with the recorded one; nothing is downloaded or written."""
    return fingerprint(read_issue(ticket_id, coordinates))


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
    (raw_dir / "raw.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "title": issue["title"],
        "state": issue["state"],
        "url": issue["html_url"],
        "fingerprint": fingerprint(raw),
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
