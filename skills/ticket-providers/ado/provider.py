#!/usr/bin/env python3
"""
The Azure DevOps provider's entry points.

Everything here is invoked through ticket-common/ticket.py and is never read by
a driver. Each function is handed the context the front door built and the
flags it did not recognise, so an ADO-only option never reaches the front door's
parser.

The organization and project always come from `ctx["coordinates"]`: the
ticket's own where it has them, else the binding of the product it is filed
under. Nothing here opens a config file, which is what lets several products
each be bound to a different project.
"""

import argparse
import urllib.parse
from pathlib import Path

from ticketlib import providers, tickets, tokencache
from ticketlib.errors import EXIT_ERROR, TicketError

SOURCE = "ado"

DEFAULT_ORG = "edwire"
DEFAULT_PROJECT = "EW.Educate"

API_VERSION = "7.1"

_auth = providers.load_private(SOURCE, "_auth")


def binding(ctx: dict, extra: list[str]) -> dict:
    """
    The coordinates an init would bind, without validating them.

    A flag the user gave wins; otherwise what the target product already
    inherits — so a second product in a bound namespace needs only its
    project — and only then this source's own default.
    """
    parser = argparse.ArgumentParser(prog="ticket.py init --source ado")
    parser.add_argument("--org")
    parser.add_argument("--project")
    args = parser.parse_args(extra)

    inherited = ctx.get("binding") or {}
    chosen: dict[str, str] = {}
    defaults_applied: list[str] = []
    inherited_applied: list[str] = []

    for name, given, default in (
        ("organization", args.org, DEFAULT_ORG),
        ("project", args.project, DEFAULT_PROJECT),
    ):
        if given:
            chosen[name] = given
        elif inherited.get(name):
            chosen[name] = str(inherited[name])
            inherited_applied.append(name)
        else:
            chosen[name] = default
            defaults_applied.append(name)

    return {
        "coordinates": chosen,
        "defaults_applied": defaults_applied,
        "inherited": inherited_applied,
    }


def init(ctx: dict, extra: list[str]) -> dict:
    org, project = _auth.coordinates(ctx)

    print("Acquiring an Azure DevOps access token via the Azure CLI…")
    token, error = _auth.fetch_cli_token()
    if error:
        raise TicketError(error, EXIT_ERROR, _auth.AZ_LOGIN_HINT)

    print("Validating the token against Azure DevOps…")
    validate(org, project, token)
    print("Token validated successfully.")

    tokencache.save(SOURCE, org, token)

    return {
        "organization": org,
        "project": project,
        "token_expires": tokencache.local_expiry_text(token),
    }


def validate(org: str, project: str, token: dict) -> None:
    import urllib.error
    import urllib.request

    url = (
        f"https://dev.azure.com/{org}/_apis/projects/"
        f"{urllib.parse.quote(project, safe='')}?api-version={API_VERSION}"
    )
    request = urllib.request.Request(url)
    request.add_header("Authorization", tokencache.make_auth_header(token))

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status == 200:
                return
            raise TicketError(
                f"Validation failed — unexpected status {response.status}"
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise TicketError(
                "Validation failed — Azure DevOps rejected the token.",
                EXIT_ERROR,
                _auth.AZ_LOGIN_HINT,
            ) from exc
        if exc.code == 403:
            raise TicketError(
                f"Validation failed — access denied to project '{project}' in '{org}'."
            ) from exc
        if exc.code == 404:
            raise TicketError(
                f"Validation failed — project '{project}' not found in organization '{org}'."
            ) from exc
        raise TicketError(f"Validation failed — HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise TicketError(f"Validation failed — network error: {exc.reason}") from exc


def fetch(ctx: dict, extra: list[str]) -> dict:
    org, project = _auth.coordinates(ctx)
    fetch_module = providers.load_private(SOURCE, "_fetch")
    return fetch_module.run(ctx["location"], org, project, _auth.auth_header(org))


def propose_new(ctx: dict, title: str, ticket_type: str | None, extra: list[str]) -> dict:
    """What `new` would send, built without writing anything. Reads the project's types."""
    parser = argparse.ArgumentParser(prog="ticket.py new --source ado")
    parser.add_argument("--body-file")
    parser.add_argument("--criteria-file")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--parent")
    args = parser.parse_args(extra)

    org, project = _auth.coordinates(ctx)
    new_module = providers.load_private(SOURCE, "_new")

    parent_id = None
    if args.parent:
        if ticket_type != "task":
            raise TicketError(
                f"only a task may have a parent, not a {ticket_type}", EXIT_ERROR
            )
        parent_id = args.parent.strip().removeprefix("ado:").removeprefix("#")
        if not parent_id.isdigit():
            raise TicketError(
                f"'{args.parent}' is not a work item id",
                EXIT_ERROR,
                "Pass the parent as an id or `ado:{id}`.",
            )

    available = new_module.project_types(org, project, _auth.auth_header(org))
    native = new_module.native_type(ticket_type or "", available)

    tags = list(args.tag)
    type_tag = new_module.TAG_BY_TYPE.get(ticket_type or "")
    if type_tag and type_tag not in (tag.lower() for tag in tags):
        tags.append(type_tag)

    return {
        "organization": org,
        "project": project,
        "title": title,
        "type": ticket_type,
        "native_type": native,
        "labels": tags,
        "body": _read(args.body_file),
        "acceptance_criteria": _read(args.criteria_file),
        "parent": f"ado:{parent_id}" if parent_id else None,
    }


def _read(path: str | None) -> str:
    if not path:
        return ""
    source = Path(path).expanduser()
    if not source.is_file():
        raise TicketError(f"file not found: {source}", EXIT_ERROR)
    return source.read_text(encoding="utf-8").strip()


def new(ctx: dict, title: str, ticket_type: str | None, extra: list[str]) -> dict:
    proposal = propose_new(ctx, title, ticket_type, extra)
    org, project = proposal["organization"], proposal["project"]
    new_module = providers.load_private(SOURCE, "_new")
    parent_id = (proposal["parent"] or "").removeprefix("ado:") or None

    created = new_module.create(
        org,
        project,
        _auth.auth_header(org),
        proposal["native_type"],
        new_module.patch_document(
            org,
            title,
            proposal["body"],
            proposal["acceptance_criteria"],
            proposal["labels"],
            parent_id,
        ),
    )
    if not created.get("id"):
        raise TicketError("Azure DevOps did not report the id of the work item it created")
    return {
        "id": str(created["id"]),
        "url": f"https://dev.azure.com/{org}/{urllib.parse.quote(project)}"
        f"/_workitems/edit/{created['id']}",
        **proposal,
    }


def propose_update(ctx: dict, extra: list[str]) -> dict:
    """
    The before and after of an update, built from the local snapshot and written nowhere.

    The snapshot's revision travels with the proposal: the write asserts it, so
    an edit made between the drift check and the write is refused by Azure
    DevOps itself rather than overwritten.
    """
    parser = argparse.ArgumentParser(prog="ticket.py update (ado)")
    parser.add_argument("--title")
    parser.add_argument("--description-file")
    parser.add_argument("--criteria-file")
    parser.add_argument("--state")
    parser.add_argument("--add-tag", action="append", default=[])
    parser.add_argument("--remove-tag", action="append", default=[])
    args = parser.parse_args(extra)

    org, project = _auth.coordinates(ctx)
    update_module = providers.load_private(SOURCE, "_update")
    snapshot = update_module.read_snapshot(ctx["location"], ctx["id"])

    fields = snapshot["fields"]
    tags = [tag.strip() for tag in str(fields.get(update_module.TAGS_FIELD) or "").split(";") if tag.strip()]
    removed = {tag.lower() for tag in args.remove_tag}
    new_tags = [tag for tag in tags if tag.lower() not in removed]
    new_tags += [tag for tag in args.add_tag if tag.lower() not in {t.lower() for t in new_tags}]

    before = {
        "title": fields.get("System.Title"),
        "description": fields.get(update_module.DESCRIPTION_FIELD) or "",
        "acceptance_criteria": fields.get(update_module.CRITERIA_FIELD) or "",
        "state": fields.get("System.State"),
        "labels": tags,
    }
    after = {
        "title": args.title if args.title is not None else before["title"],
        "description": _read(args.description_file) if args.description_file else before["description"],
        "acceptance_criteria": _read(args.criteria_file) if args.criteria_file else before["acceptance_criteria"],
        "state": args.state or before["state"],
        "labels": new_tags,
    }
    changes = [
        {"field": field, "before": before[field], "after": after[field]}
        for field in before
        if before[field] != after[field]
    ]

    return {
        "organization": org,
        "project": snapshot["project"] or project,
        "revision": snapshot["rev"],
        "changes": changes,
        "payload": update_module.patch_document(snapshot["rev"], changes),
        "payload_is_empty": not changes,
    }


def update(ctx: dict, extra: list[str]) -> dict:
    proposal = propose_update(ctx, extra)
    if proposal["payload_is_empty"]:
        return {**proposal, "written": False}
    update_module = providers.load_private(SOURCE, "_update")
    org = proposal["organization"]
    update_module.write(
        org, proposal["project"], ctx["id"], _auth.auth_header(org), proposal["payload"]
    )
    return {**proposal, "written": True}


def publish(ctx: dict, text: str, extra: list[str]) -> dict:
    org, project = _auth.coordinates(ctx)
    comment_module = providers.load_private(SOURCE, "_comment")
    return comment_module.run(ctx["id"], org, project, _auth.auth_header(org), text)


def drift(ctx: dict, extra: list[str]) -> dict:
    org, project = _auth.coordinates(ctx)
    drift_module = providers.load_private(SOURCE, "_drift")
    record = tickets.load(ctx["location"])
    return drift_module.run(
        ctx["location"], org, project, _auth.auth_header(org), record
    )


def auth_status(ctx: dict) -> dict:
    coordinates = ctx.get("coordinates") or {}
    org = coordinates.get("organization")
    token = tokencache.load(SOURCE, str(org)) if org else None
    return {
        "organization": org,
        "project": coordinates.get("project"),
        "credential": "azure-cli bearer token",
        "status": tokencache.describe(token),
        "usable": tokencache.is_usable(token),
    }
