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
