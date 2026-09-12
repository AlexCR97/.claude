#!/usr/bin/env python3
"""
The Azure DevOps provider's entry points.

Everything here is invoked through ticket-common/ticket.py and is never read by
a driver. Each function is handed the context the front door built and the
flags it did not recognise, so an ADO-only option never reaches the front door's
parser.
"""

import argparse
import urllib.parse

from ticketlib import config, providers, tokencache
from ticketlib.errors import EXIT_ERROR, TicketError

SOURCE = "ado"

DEFAULT_ORG = "edwire"
DEFAULT_PROJECT = "EW.Educate"

API_VERSION = "7.1"

_auth = providers.load_private(SOURCE, "_auth")


def init(ctx: dict, extra: list[str]) -> dict:
    parser = argparse.ArgumentParser(prog="ticket.py init --source ado")
    parser.add_argument("--org", default=DEFAULT_ORG)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    args = parser.parse_args(extra)

    print("Acquiring an Azure DevOps access token via the Azure CLI…")
    token, error = _auth.fetch_cli_token()
    if error:
        raise TicketError(error, EXIT_ERROR, _auth.AZ_LOGIN_HINT)

    print("Validating the token against Azure DevOps…")
    validate(args.org, args.project, token)
    print("Token validated successfully.")

    config.save_source(
        SOURCE,
        {"organization": args.org, "project": args.project, "token": token},
    )

    return {
        "organization": args.org,
        "project": args.project,
        "token_expires": tokencache.local_expiry_text(token),
        "defaults_applied": [
            name
            for name, value, default in (
                ("organization", args.org, DEFAULT_ORG),
                ("project", args.project, DEFAULT_PROJECT),
            )
            if value == default
        ],
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
            raise TicketError(f"Validation failed — unexpected status {response.status}")
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
    org, project = _auth.coordinates()
    fetch_module = providers.load_private(SOURCE, "_fetch")
    return fetch_module.run(ctx["id"], org, project, _auth.auth_header())


def publish(ctx: dict, text: str, extra: list[str]) -> dict:
    org, project = _auth.coordinates()
    comment_module = providers.load_private(SOURCE, "_comment")
    return comment_module.run(ctx["id"], org, project, _auth.auth_header(), text)


def drift(ctx: dict, extra: list[str]) -> dict:
    from ticketlib import tickets

    drift_module = providers.load_private(SOURCE, "_drift")
    record = tickets.load(SOURCE, ctx["id"])
    return drift_module.run(ctx["id"], _auth.auth_header(), record)


def auth_status(ctx: dict) -> dict:
    stored = config.load_source(SOURCE)
    token = stored.get("token")
    return {
        "organization": stored.get("organization"),
        "project": stored.get("project"),
        "credential": "azure-cli bearer token",
        "status": tokencache.describe(token),
        "usable": tokencache.is_usable(token),
    }
