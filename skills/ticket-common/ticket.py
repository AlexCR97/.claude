#!/usr/bin/env python3
"""
The single command every ticket-* driver invokes.

A driver globs `ticket-providers/*/` and so does not know the source names at
authoring time — which means a command string containing `{source}` could never
be pinned in `allowed-tools`. One front door means each SKILL.md names one
command, and adding a source changes no SKILL.md at all.

It is also the one place the shared preamble lives: reference resolution, config
loading, `~` expansion, ticket-directory creation, and the exit-code mapping.

Usage:
    python ticket.py sources [--check]
    python ticket.py resolve <ref> [--source S] [--type T] [--require a,b]
    python ticket.py migrate [--dry-run]
    python ticket.py init --source S [provider flags...]
    python ticket.py fetch <ref> [--source S]
    python ticket.py new --source S --title "..." [--id SLUG] [--type T]
    python ticket.py publish <ref> --file F [--delete-after-post]
    python ticket.py drift <ref>
    python ticket.py auth-status [--source S]
    python ticket.py list

Exit codes:
    0  ok — for `drift`, also "up to date"
    1  error / not initialized
    2  `--require` unmet, or `drift` found the ticket moved
    3  ambiguous bare id, or the source declares this capability absent
    4  the legacy ~/.az-workitems layout was detected — run /ticket-init
    5  ticket not found
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# A Windows console defaults to a legacy codepage, which turns any non-ASCII
# character in a ticket title or an error into mojibake.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from ticketlib import config, paths, providers, sources, tickets
from ticketlib.errors import (
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    TicketError,
)


def emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def parse_require(raw: str | None) -> list[str]:
    if not raw:
        return []
    names = [name.strip() for name in raw.split(",") if name.strip()]
    unknown = [name for name in names if name not in sources.REQUIREMENTS]
    if unknown:
        raise TicketError(
            "unknown --require value(s): " + ", ".join(unknown),
            EXIT_ERROR,
            "Accepted: " + ", ".join(sources.REQUIREMENTS) + ".",
        )
    return names


def provider_for(source: str, capability: str | None = None):
    if capability:
        providers.require_capability(source, capability)
    return providers.load_module(source)


def context(source: str, ticket_id: str = "") -> dict:
    """What every provider entry point is handed, so none rebuilds it."""
    manifest = providers.load_manifest(source)
    ctx = {
        "source": source,
        "id": ticket_id,
        "manifest": manifest,
        "config": config.load_source(source),
        "provider_dir": str(providers.provider_dir(source)),
        "tickets_home": str(paths.tickets_home()),
        "source_dir": str(paths.source_dir(source)),
    }
    if ticket_id:
        ctx["ticket_dir"] = str(paths.ticket_dir(source, ticket_id))
        ctx["paths"] = paths.ticket_paths(source, ticket_id)
    return ctx


# --- verbs ------------------------------------------------------------------


def verb_sources(args: argparse.Namespace) -> int:
    report, problems = providers.check()

    if args.check:
        emit(
            {
                "sources": report,
                "problems": problems,
                "ok": not problems,
                "providers_root": str(providers.providers_root()),
                "types_root": str(providers.types_root()),
                "known_types": providers.list_types(),
            }
        )
        return EXIT_OK if not problems else EXIT_ERROR

    emit(
        {
            "default_source": config.default_source(),
            "tickets_home": str(paths.tickets_home()),
            "providers_root": str(providers.providers_root()),
            "types_root": str(providers.types_root()),
            "known_types": providers.list_types(),
            "sources": report,
        }
    )
    return EXIT_OK


def verb_resolve(args: argparse.Namespace) -> int:
    resolved = sources.resolve(
        args.ref,
        explicit_source=args.source,
        type_override=args.type,
        require=parse_require(args.require),
    )
    emit(resolved)
    return EXIT_OK


def verb_list(args: argparse.Namespace) -> int:
    emit({"tickets_home": str(paths.tickets_home()), "tickets": tickets.list_all()})
    return EXIT_OK


def verb_migrate(args: argparse.Namespace) -> int:
    """
    Dispatch to the migration script.

    It is a verb rather than a script a driver invokes by name for the same
    reason every other verb is: a driver names one command, and a script
    filename in a SKILL.md is exactly the kind of detail that goes stale.
    """
    import subprocess

    script = Path(__file__).resolve().parent / "migrate-az-workitems.py"
    if not script.is_file():
        raise TicketError(f"migration script not found: {script}")

    command = [sys.executable, str(script)]
    if args.dry_run:
        command.append("--dry-run")

    return subprocess.run(command, check=False).returncode


def verb_init(args: argparse.Namespace) -> int:
    source, _ = sources.resolve_source(None, args.source)
    module = provider_for(source)

    result = module.init(context(source), args.extra)

    # A source becoming usable is not a decision to make it the default: an
    # init that silently repointed `default_source` would move every bare id.
    if config.default_source() is None:
        config.set_default_source(source)
        result["default_source_set_to"] = source

    result.setdefault("source", source)
    result["source_config"] = str(paths.source_config_path(source))
    result["config"] = config.redact(config.load_source(source))
    emit(result)
    return EXIT_OK


def verb_fetch(args: argparse.Namespace) -> int:
    source, ticket_id = sources.resolve_source(args.ref, args.source)
    module = provider_for(source, "fetch")

    if not config.is_initialized(source):
        raise TicketError(
            f"source '{source}' is not initialized",
            EXIT_ERROR,
            f"Run `/ticket-init {source}` first.",
        )

    ticket_dir = paths.ticket_dir(source, ticket_id)
    (ticket_dir / "raw").mkdir(parents=True, exist_ok=True)

    result = module.fetch(context(source, ticket_id), args.extra)
    result.setdefault("source", source)
    result.setdefault("id", ticket_id)
    result["paths"] = paths.ticket_paths(source, ticket_id)
    result["ticket_json"] = tickets.load(source, ticket_id)
    emit(result)
    return EXIT_OK


def verb_new(args: argparse.Namespace) -> int:
    source, _ = sources.resolve_source(None, args.source)
    module = provider_for(source, "new")

    if not args.title:
        raise TicketError("--title is required", EXIT_ERROR)

    ticket_id = args.id or slugify(args.title)
    if not ticket_id:
        raise TicketError(
            "could not derive an id from the title",
            EXIT_ERROR,
            "Pass --id explicitly.",
        )

    sources.validate_id(source, ticket_id)

    if paths.ticket_dir(source, ticket_id).exists():
        raise TicketError(
            f"{source}:{ticket_id} already exists",
            EXIT_ERROR,
            f"Pass a different --id, or open {paths.ticket_dir(source, ticket_id)}.",
        )

    result = module.new(context(source, ticket_id), args.title, args.type, args.extra)
    result.setdefault("source", source)
    result.setdefault("id", ticket_id)
    result["paths"] = paths.ticket_paths(source, ticket_id)
    result["ticket_json"] = tickets.load(source, ticket_id)
    emit(result)
    return EXIT_OK


def verb_publish(args: argparse.Namespace) -> int:
    source, ticket_id = sources.resolve_source(args.ref, args.source)
    module = provider_for(source, "publish")

    # Neither Python nor a quoted shell argument expands a leading ~.
    comment_path = Path(args.file).expanduser()
    if not comment_path.is_file():
        raise TicketError(f"comment file not found: {comment_path}", EXIT_NOT_FOUND)

    text = comment_path.read_text(encoding="utf-8").strip()
    if not text:
        raise TicketError(f"comment file is empty: {comment_path}", EXIT_ERROR)

    result = module.publish(context(source, ticket_id), text, args.extra)
    result.setdefault("source", source)
    result.setdefault("id", ticket_id)

    if args.delete_after_post:
        comment_path.unlink()
        result["deleted"] = str(comment_path)

    emit(result)
    return EXIT_OK


def verb_drift(args: argparse.Namespace) -> int:
    source, ticket_id = sources.resolve_source(args.ref, args.source)
    module = provider_for(source, "drift")

    result = module.drift(context(source, ticket_id), args.extra)
    result.setdefault("source", source)
    result.setdefault("id", ticket_id)
    emit(result)

    from ticketlib.errors import EXIT_DRIFTED

    return EXIT_DRIFTED if result.get("is_stale") else EXIT_OK


def verb_auth_status(args: argparse.Namespace) -> int:
    names = [args.source] if args.source else providers.list_sources()
    statuses = []
    for source in names:
        sources.require_installed(source, "--source names")
        module = providers.load_module(source)
        status = module.auth_status(context(source))
        status.setdefault("source", source)
        status["initialized"] = config.is_initialized(source)
        statuses.append(status)

    emit({"sources": statuses})
    return EXIT_OK


def slugify(title: str) -> str:
    """
    A fallback id for a store that has no upstream numbering.

    Drivers own the slug they pass in `--id`; this is only what happens when
    none was given.
    """
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(slug.split("-")[:8])


# --- entry point ------------------------------------------------------------


VERBS = {
    "sources": verb_sources,
    "resolve": verb_resolve,
    "list": verb_list,
    "migrate": verb_migrate,
    "init": verb_init,
    "fetch": verb_fetch,
    "new": verb_new,
    "publish": verb_publish,
    "drift": verb_drift,
    "auth-status": verb_auth_status,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ticket.py",
        description="The single front door for the ticket-* skills.",
    )
    sub = parser.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("sources", help="list every provider and its capabilities")
    p.add_argument(
        "--check",
        action="store_true",
        help="validate that capabilities and role files agree",
    )

    p = sub.add_parser("resolve", help="resolve a reference to a source, id and paths")
    p.add_argument("ref", nargs="?", help="[source:]id")
    p.add_argument("--source")
    p.add_argument("--type", help="override the ticket type and record it")
    p.add_argument(
        "--require",
        help="comma-separated: " + ", ".join(sources.REQUIREMENTS),
    )

    sub.add_parser("list", help="every ticket on disk, across every source")

    p = sub.add_parser(
        "migrate", help="copy data from the pre-~/.tickets layout into this one"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="report what would happen, change nothing"
    )

    p = sub.add_parser("init", help="per-source connection setup")
    p.add_argument("--source")

    p = sub.add_parser("fetch", help="refresh the local snapshot (remote sources)")
    p.add_argument("ref")
    p.add_argument("--source")

    p = sub.add_parser("new", help="create a ticket in a store that supports it")
    p.add_argument("--source")
    p.add_argument("--title", required=True)
    p.add_argument("--id", help="the slug or id to use; derived from the title if absent")
    p.add_argument("--type")

    p = sub.add_parser("publish", help="post a refinement summary back to the source")
    p.add_argument("ref")
    p.add_argument("--source")
    p.add_argument("--file", required=True)
    p.add_argument("--delete-after-post", action="store_true")

    p = sub.add_parser("drift", help="has the ticket moved since it was fetched?")
    p.add_argument("ref")
    p.add_argument("--source")

    p = sub.add_parser("auth-status", help="report each source's credential state")
    p.add_argument("--source")

    return parser


def main() -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args()
    # Provider-specific flags are passed through untouched, so the front door
    # never has to know what any one source needs to connect.
    args.extra = extra

    try:
        return VERBS[args.verb](args)
    except TicketError as exc:
        print(f"ERROR: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(exc.hint, file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
