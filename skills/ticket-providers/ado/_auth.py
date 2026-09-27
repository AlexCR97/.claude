#!/usr/bin/env python3
"""
Azure DevOps credentials.

dev.azure.com accepts an Azure CLI access token as a bearer credential, so the
whole `az account get-access-token` response is cached in the credential store,
keyed by organization, and replaced as it nears expiry. There is no PAT, and the
user is never asked for one — they only need to stay signed in with `az login`.

The caching mechanics themselves are not ADO's: they live in
ticketlib/tokencache.py and would serve any bearer-token source. What is ADO's
is the resource id below and the fact that the Azure CLI is the issuer.
"""

import json

from ticketlib import proc, tokencache

SOURCE = "ado"

# The audience an access token must be issued for to be accepted by dev.azure.com.
AZURE_DEVOPS_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"

AZ_LOGIN_HINT = (
    "Sign in with 'az login' so an Azure DevOps token can be acquired, then "
    "re-run this skill."
)


def fetch_cli_token() -> tuple[dict, str]:
    """Returns (token, error_message); token is empty when acquisition failed."""
    code, stdout, stderr = proc.run(
        ["az", "account", "get-access-token", "--resource", AZURE_DEVOPS_RESOURCE_ID],
        timeout=60,
    )

    if code == -1:
        return {}, stderr
    if code != 0:
        detail = stderr.strip() or f"exit code {code}"
        return {}, f"Azure CLI failed to acquire an access token — {detail}"

    try:
        token = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return {}, f"Azure CLI returned output that is not JSON — {exc}"

    if not token.get("accessToken"):
        return {}, "Azure CLI response carried no access token."

    return token, ""


def get_token(org: str) -> tuple[dict, str]:
    """Returns (token, error_message); token is empty when acquisition failed."""
    cached = tokencache.load(SOURCE, org)
    if cached and tokencache.is_usable(cached):
        return cached, ""

    token, error = fetch_cli_token()
    if error:
        return {}, error

    tokencache.save(SOURCE, org, token)
    return token, ""


def require_token(org: str) -> dict:
    from ticketlib.errors import EXIT_ERROR, TicketError

    token, error = get_token(org)
    if token:
        return token

    raise TicketError(error, EXIT_ERROR, AZ_LOGIN_HINT)


def auth_header(org: str) -> str:
    return tokencache.make_auth_header(require_token(org))


def coordinates(ctx: dict) -> tuple[str, str]:
    """The organization and project this ticket, or the product it is filed under, points at."""
    from ticketlib.errors import EXIT_ERROR, TicketError

    values = ctx.get("coordinates") or {}
    org = values.get("organization")
    project = values.get("project")
    if not org or not project:
        where = ctx.get("product") or "this product"
        raise TicketError(
            f"no Azure DevOps organization and project are bound for {where}",
            EXIT_ERROR,
            f"Run `/ticket-init ado --in {where}` first.",
        )
    return str(org), str(project)
