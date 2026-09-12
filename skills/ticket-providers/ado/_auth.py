#!/usr/bin/env python3
"""
Azure DevOps credentials.

dev.azure.com accepts an Azure CLI access token as a bearer credential, so the
whole `az account get-access-token` response is cached in this source's
config.json and replaced as it nears expiry. There is no PAT, and the user is
never asked for one — they only need to stay signed in with `az login`.

The caching mechanics themselves are not ADO's: they live in
ticketlib/tokencache.py and would serve any bearer-token source. What is ADO's
is the resource id below and the fact that the Azure CLI is the issuer.
"""

import json

from ticketlib import config, proc, tokencache

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


def get_token() -> tuple[dict, str]:
    """Returns (token, error_message); token is empty when acquisition failed."""
    stored = config.load_source(SOURCE)
    cached = stored.get("token")
    if tokencache.is_usable(cached):
        return cached, ""

    token, error = fetch_cli_token()
    if error:
        return {}, error

    # Creating a config here would omit the organization and project that
    # /ticket-init writes.
    if stored:
        stored["token"] = token
        config.save_source(SOURCE, stored)

    return token, ""


def require_token() -> dict:
    from ticketlib.errors import EXIT_ERROR, TicketError

    token, error = get_token()
    if token:
        return token

    raise TicketError(error, EXIT_ERROR, AZ_LOGIN_HINT)


def auth_header() -> str:
    return tokencache.make_auth_header(require_token())


def coordinates() -> tuple[str, str]:
    """The organization and project this machine is pointed at."""
    from ticketlib.errors import EXIT_ERROR, TicketError

    stored = config.load_source(SOURCE)
    org = stored.get("organization")
    project = stored.get("project")
    if not org or not project:
        raise TicketError(
            "no Azure DevOps organization and project are configured",
            EXIT_ERROR,
            "Run `/ticket-init ado` first.",
        )
    return str(org), str(project)
