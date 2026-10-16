#!/usr/bin/env python3
"""
Azure DevOps coordinates.

There is no credential here: `az` signs every request itself, so the user only
needs to stay signed in with `az login`.
"""

from ticketlib.errors import EXIT_ERROR, TicketError


def coordinates(ctx: dict) -> tuple[str, str]:
    """The organization and project this ticket, or the product it is filed under, points at."""
    values = ctx.get("coordinates") or {}
    org = values.get("organization")
    project = values.get("project")
    if not org or not project:
        where = ctx.get("product") or "this product"
        raise TicketError(
            f"no Azure DevOps organization and project are bound for {where}",
            EXIT_ERROR,
            f"Run `/ticket-setup ado --in {where}` first.",
        )
    return str(org), str(project)
