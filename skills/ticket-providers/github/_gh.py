#!/usr/bin/env python3
"""
Everything this provider does, it does through the `gh` CLI.

That is the whole credential story: `gh` already holds the user's GitHub
authentication, refreshes it, and knows about enterprise hosts and SSO. **No
token is ever stored by this suite** — `{source}/config.json` holds only the
repository, and there is nothing in it worth protecting.
"""

import json

from ticketlib import config, proc
from ticketlib.errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError

SOURCE = "github"

GH_HINT = (
    "Install the GitHub CLI and run `gh auth login`, then re-run this skill. "
    "This suite never stores a GitHub token of its own."
)


def run(args: list[str], stdin_text: str | None = None) -> tuple[int, str, str]:
    return proc.run(["gh", *args], timeout=120, stdin_text=stdin_text)


def require_cli() -> None:
    if proc.which("gh") is None:
        raise TicketError("the GitHub CLI ('gh') was not found on PATH", EXIT_ERROR, GH_HINT)


def auth_state() -> tuple[bool, str]:
    """Returns (signed_in, detail). `gh auth status` writes its report to stderr."""
    if proc.which("gh") is None:
        return False, "the GitHub CLI ('gh') was not found on PATH"

    code, stdout, stderr = run(["auth", "status"])
    # The report is several lines of host/account/scope detail. One line is
    # what a driver shows; the rest is noise in a status row.
    lines = [line.strip() for line in (stderr or stdout).splitlines() if line.strip()]
    detail = next(
        (line for line in lines if "Logged in" in line or "not logged" in line.lower()),
        lines[0] if lines else "",
    )
    return code == 0, detail


def require_auth() -> None:
    require_cli()
    signed_in, detail = auth_state()
    if not signed_in:
        raise TicketError(f"not signed in to GitHub — {detail}", EXIT_ERROR, GH_HINT)


def repository() -> str:
    repo = config.load_source(SOURCE).get("repository")
    if not repo:
        raise TicketError(
            "no GitHub repository is configured",
            EXIT_ERROR,
            "Run `/ticket-init github --repo owner/name` first.",
        )
    return str(repo)


def api(path: str, paginate: bool = False) -> object:
    """One `gh api` call, returning parsed JSON."""
    require_auth()
    args = ["api", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        # --slurp so a paginated array comes back as one JSON document rather
        # than several concatenated ones, which json.loads cannot read.
        args.extend(["--paginate", "--slurp"])

    code, stdout, stderr = run(args)
    if code != 0:
        detail = stderr.strip() or f"exit code {code}"
        if "404" in detail or "Not Found" in detail:
            raise TicketError(f"not found: {path}", EXIT_NOT_FOUND, detail)
        raise TicketError(f"`gh api {path}` failed — {detail}")

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise TicketError(f"`gh api {path}` returned output that is not JSON — {exc}") from exc

    # --slurp nests each page as a list; flatten to the single array callers want.
    if paginate and isinstance(payload, list):
        flattened: list = []
        for page in payload:
            flattened.extend(page if isinstance(page, list) else [page])
        return flattened

    return payload
