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

from ticketlib import azrest, proc, providers
from ticketlib.errors import EXIT_ERROR, TicketError

SOURCE = "ado"

DEFAULT_ORG = "edwire"
DEFAULT_PROJECT = "EW.Educate"

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


def require_cli() -> None:
    """
    The Azure CLI, a sign-in, and the `azure-devops` extension that `az boards` is part of.

    The extension is checked here because the update and create recipes use it
    and nothing else would notice it missing until the first write.
    """
    if proc.which("az") is None:
        raise TicketError(
            "the Azure CLI ('az') was not found on PATH",
            EXIT_ERROR,
            "Install it, run `az login`, then re-run this skill.",
        )

    code, _, stderr = proc.run(["az", "account", "show", "--output", "none"])
    if code != 0:
        raise TicketError(
            f"not signed in to Azure — {stderr.strip() or f'exit code {code}'}",
            EXIT_ERROR,
            azrest.AZ_LOGIN_HINT,
        )

    code, _, _ = proc.run(["az", "extension", "show", "--name", "azure-devops", "--output", "none"])
    if code != 0:
        raise TicketError(
            "the Azure CLI's `azure-devops` extension is not installed",
            EXIT_ERROR,
            "Run `az extension add --name azure-devops`, then re-run this skill.",
        )


def init(ctx: dict, extra: list[str]) -> dict:
    org, project = _auth.coordinates(ctx)

    require_cli()
    print(f"Validating access to {project} in {org} through the Azure CLI…")
    validate(org, project)
    print("Access validated.")

    return {
        "organization": org,
        "project": project,
        "credential": "delegated to the Azure CLI; nothing stored",
    }


def validate(org: str, project: str) -> None:
    url = f"https://dev.azure.com/{org}/_apis/projects/{urllib.parse.quote(project, safe='')}"
    try:
        azrest.get_json(url)
    except azrest.AzRestError as exc:
        detail = str(exc)
        if "Forbidden" in detail:
            raise TicketError(
                f"Validation failed — access denied to project '{project}' in '{org}'."
            ) from exc
        if "Not Found" in detail:
            raise TicketError(
                f"Validation failed — project '{project}' not found in organization '{org}'."
            ) from exc
        raise TicketError(f"Validation failed — {detail}") from exc


def fetch(ctx: dict, extra: list[str]) -> dict:
    org, project = _auth.coordinates(ctx)
    fetch_module = providers.load_private(SOURCE, "_fetch")
    return fetch_module.run(ctx["location"], org, project)
