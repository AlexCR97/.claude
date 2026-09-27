#!/usr/bin/env python3
"""
The single command every ticket-* driver invokes.

A driver globs `ticket-providers/*/` and so does not know the source names at
authoring time — which means a command string containing `{source}` could never
be pinned in `allowed-tools`. One front door means each SKILL.md names one
command, and adding a source changes no SKILL.md at all.

It is also the one place the shared preamble lives: reference resolution,
filing, config merging, `~` expansion, ticket-directory creation, and the
exit-code mapping.

Usage:
    python ticket.py sources [--check]
    python ticket.py resolve [<ref>] [--source S] [--type T] [--require a,b] [--in X] [--context X]
    python ticket.py list [--in X] [--context X]
    python ticket.py namespaces [--in X]
    python ticket.py defaults [--namespace NS] [--product NS/PRODUCT]
    python ticket.py migrate [--dry-run] [--map SOURCE=NS/PRODUCT ...]
    python ticket.py init --source S [--in NS/PRODUCT] [--propose] [provider flags...]
    python ticket.py init --in NS[/PRODUCT]
    python ticket.py fetch <ref> [--source S] [--in X] [--context X]
    python ticket.py new --source S --title "..." [--id SLUG] [--type T] [--in X] [--context X] [--propose] [provider flags...]
    python ticket.py publish <ref> --file F [--delete-after-post]
    python ticket.py drift <ref>
    python ticket.py move <ref> --to NS/PRODUCT [--dry-run]
    python ticket.py auth-status [--source S] [--in X]
    python ticket.py scan-roots [--in NS[/PRODUCT]] [--set [DIR ...]]

`--in` restricts to a namespace or product; `--context` only prefers one — it
is how a driver passes the session context, which must never hide a ticket
filed elsewhere.

Exit codes:
    0  ok — for `drift`, also "up to date"
    1  error / not initialized
    2  `--require` unmet, or `drift` found the ticket moved
    3  ambiguous reference or filing, or the source declares this capability absent
    4  an older layout was detected — run /ticket-init to migrate it
    5  ticket, namespace or product not found
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# A Windows console defaults to a legacy codepage, which turns any non-ASCII
# character in a ticket title or an error into mojibake.
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")

from ticketlib import (
    bindings,
    config,
    filing,
    layout,
    moves,
    paths,
    providers,
    sources,
    tickets,
)
from ticketlib.errors import (
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    TicketError,
)
from ticketlib.layout import Location, Product, Scope


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


def restrict_of(args: argparse.Namespace) -> Scope | None:
    return sources.optional_scope(getattr(args, "within", None))


def context_of(args: argparse.Namespace) -> Scope | None:
    return sources.optional_scope(getattr(args, "context", None))


def locate(args: argparse.Namespace) -> sources.Target:
    layout.require_current()
    return sources.locate(
        args.ref, args.source, restrict_of(args), context_of(args), Path.cwd()
    )


def require_filed(target: sources.Target) -> Location:
    location = target.location
    if not target.filed:
        raise TicketError(
            f"{location.qualified} is not on disk",
            EXIT_NOT_FOUND,
            sources.requirement_hint(location, ["ticket_dir"]),
        )
    return location


def location_report(target: sources.Target) -> dict:
    location = target.location
    return {
        "source": location.source,
        "id": location.id,
        "ref": location.ref,
        "qualified_ref": location.qualified,
        "product": location.product.ref,
        "filing": target.filing.as_dict() if target.filing else None,
        "outside_context": target.outside_context,
    }


def ticket_context(location: Location, address: dict | None = None) -> dict:
    record = tickets.load(location)
    coordinates = sources.ticket_coordinates(location, record, address)
    return sources.provider_context(
        location.source, location.product, location, coordinates
    )


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
            "default_namespace": config.default_namespace(),
            "tickets_home": str(paths.tickets_home()),
            "layout": layout.version(),
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
        restrict=restrict_of(args),
        context=context_of(args),
        cwd=Path.cwd(),
    )
    emit(resolved)
    return EXIT_OK


def verb_list(args: argparse.Namespace) -> int:
    layout.require_current()
    context = context_of(args)
    entries = tickets.list_all(restrict_of(args))

    for entry in entries:
        namespace, _, name = entry["product"].partition("/")
        product = Product(namespace, name)
        parent = entry.get("parent")
        found = sources.resolve_stored(parent, product) if parent else None
        entry["parent_ref"] = found.qualified if found else None
        if context:
            entry["in_context"] = context.contains(product)

    emit(
        {
            "tickets_home": str(paths.tickets_home()),
            "scope": args.within,
            "context": context.ref if context else None,
            "outside_context": (
                sum(1 for entry in entries if not entry["in_context"])
                if context
                else None
            ),
            "tickets": entries,
        }
    )
    return EXIT_OK


def binding_summary(product: Product) -> dict:
    """Each source's own and effective coordinates at a product, and whether they are complete."""
    summary = {}
    for source in providers.list_sources():
        declared = providers.coordinates(source)
        if not declared:
            continue
        effective = config.binding(source, product.namespace, product.name)
        own = config.own_binding(source, product.namespace, product.name)
        if not effective and not own:
            continue
        summary[source] = {
            "own": own,
            "effective": effective,
            "complete": sources.is_usable(source, effective),
        }
    return summary


def verb_namespaces(args: argparse.Namespace) -> int:
    layout.require_current()
    default_namespace = config.default_namespace()

    if args.within:
        scope = layout.parse_scope(args.within)
        directory = (
            paths.product_dir(scope.namespace, scope.product)
            if scope.product
            else paths.namespace_dir(scope.namespace)
        )
        if not directory.is_dir():
            raise TicketError(
                f"{scope.ref} does not exist",
                EXIT_NOT_FOUND,
                f"Create it with `/ticket-init --in {scope.ref}`, or run "
                "`ticket.py namespaces` to see what exists.",
            )
        merged, origins = config.effective(scope.namespace, scope.product)
        product = scope.as_product() or Product(
            scope.namespace, config.default_product(scope.namespace)
        )
        emit(
            {
                "scope": scope.ref,
                "dir": str(directory),
                "level_config": str(
                    paths.level_config_path(scope.namespace, scope.product)
                ),
                "default_product": f"{scope.namespace}/{config.default_product(scope.namespace)}",
                "is_default_namespace": scope.namespace == default_namespace,
                "bindings": binding_summary(product),
                "default_source": merged.get("default_source"),
                "scan_roots": merged.get("scan_roots") or [],
                "config": config.redact(merged),
                "config_sources": origins,
                "ticket_count": len(layout.locations(scope=scope)),
            }
        )
        return EXIT_OK

    namespaces = []
    for namespace in layout.namespaces():
        namespaces.append(
            {
                "name": namespace,
                "config": str(paths.level_config_path(namespace)),
                "default_product": config.default_product(namespace),
                "own_bindings": {
                    source: config.own_binding(source, namespace)
                    for source in providers.list_sources()
                    if config.own_binding(source, namespace)
                },
                "own_scan_roots": config.own_scan_roots(namespace),
                "products": [
                    {
                        "name": product.name,
                        "ref": product.ref,
                        "bindings": binding_summary(product),
                        "own_scan_roots": config.own_scan_roots(
                            product.namespace, product.name
                        ),
                        "ticket_count": len(layout.locations(scope=Scope.of(product))),
                    }
                    for product in layout.products(namespace)
                ],
            }
        )

    emit(
        {
            "tickets_home": str(paths.tickets_home()),
            "layout": layout.version(),
            "default_namespace": default_namespace,
            "default_product": f"{default_namespace}/{config.default_product(default_namespace)}",
            "namespaces": namespaces,
        }
    )
    return EXIT_OK


def verb_defaults(args: argparse.Namespace) -> int:
    layout.require_current()
    if args.namespace is not None or args.product is not None:
        layout.stamp_current()

    if args.namespace is not None:
        name = layout.require_name(args.namespace, "namespace")
        if name != paths.DEFAULT_NAME and not paths.namespace_dir(name).is_dir():
            raise TicketError(
                f"no namespace '{name}'",
                EXIT_NOT_FOUND,
                f"Create it with `/ticket-init --in {name}` first.",
            )
        # `default` is what an unset key already means, so it is stored as unset.
        config.update_level(
            {"default_namespace": None if name == paths.DEFAULT_NAME else name}
        )

    if args.product is not None:
        product = layout.parse_product(args.product)
        if not paths.namespace_dir(product.namespace).is_dir():
            raise TicketError(f"no namespace '{product.namespace}'", EXIT_NOT_FOUND)
        if not product.is_default and not product.dir.is_dir():
            raise TicketError(
                f"no product '{product.ref}'",
                EXIT_NOT_FOUND,
                f"Create it with `/ticket-init --in {product.ref}` first.",
            )
        config.update_level(
            {"default_product": None if product.is_default else product.name},
            product.namespace,
        )

    default_namespace = config.default_namespace()
    emit(
        {
            "default_namespace": default_namespace,
            "default_product": f"{default_namespace}/{config.default_product(default_namespace)}",
            "configured": {
                "default_namespace": config.load_root().get("default_namespace"),
                "default_products": {
                    namespace: config.load_level(namespace).get("default_product")
                    for namespace in layout.namespaces()
                    if config.load_level(namespace).get("default_product")
                },
            },
        }
    )
    return EXIT_OK


def verb_migrate(args: argparse.Namespace) -> int:
    """
    Run both migrations, oldest first, and report them as one.

    They are scripts rather than code in this file for the reason each of them
    states: renaming directories and rewriting config are the operations where
    a half-completed pass is worst, and each is a single self-contained run.
    """
    here = Path(__file__).resolve().parent
    reports = {}
    for name, script in (
        ("az_workitems", "migrate-az-workitems.py"),
        ("layout", "migrate-layout.py"),
    ):
        command = [sys.executable, str(here / script)]
        if args.dry_run:
            command.append("--dry-run")
        if name == "layout":
            for mapping in args.map or []:
                command.extend(["--map", mapping])

        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, encoding="utf-8"
        )
        if completed.returncode != 0:
            print(completed.stderr, file=sys.stderr, end="")
            raise TicketError(f"{script} failed with exit code {completed.returncode}")
        try:
            reports[name] = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise TicketError(
                f"{script} printed something that is not JSON — {exc}"
            ) from exc

    results = {report.get("result") for report in reports.values()}
    if results == {"nothing_to_migrate"}:
        result = "nothing_to_migrate"
    else:
        result = "dry_run" if args.dry_run else "migrated"

    emit({"result": result, **reports})
    return EXIT_OK


def create_scope(scope: Scope) -> int:
    layout.stamp_current()
    created = []
    namespace_dir = paths.namespace_dir(scope.namespace)
    if not namespace_dir.is_dir():
        namespace_dir.mkdir(parents=True)
        created.append(scope.namespace)
    if scope.product:
        product_dir = paths.product_dir(scope.namespace, scope.product)
        if not product_dir.is_dir():
            product_dir.mkdir(parents=True)
            created.append(scope.ref)

    emit(
        {
            "scope": scope.ref,
            "created": created,
            "dir": str(
                paths.product_dir(scope.namespace, scope.product)
                if scope.product
                else namespace_dir
            ),
            "level_config": str(
                paths.level_config_path(scope.namespace, scope.product)
            ),
        }
    )
    return EXIT_OK


def verb_init(args: argparse.Namespace) -> int:
    layout.require_current()
    target = restrict_of(args)

    if not args.source:
        if target is None:
            raise TicketError(
                "nothing to initialize",
                EXIT_ERROR,
                "Pass --source to bind a source, or --in to create a namespace or product.",
            )
        return create_scope(target)

    source = args.source
    sources.require_installed(source, "--source names")
    if target and not target.product:
        raise TicketError(
            f"--in {target.ref} names a namespace; a binding is filed under a product",
            EXIT_ERROR,
            f"Pass `--in {target.namespace}/{{product}}`.",
        )

    module = provider_for(source)
    named = target.as_product() if target else None
    proposal = module.binding(sources.provider_context(source, named), args.extra)
    coordinates = proposal.get("coordinates") or {}
    product = named or bindings.propose(source, coordinates)
    problems = bindings.problems(source, product, coordinates)

    if args.propose:
        emit(
            {
                "source": source,
                "coordinates": coordinates,
                "product": product.ref,
                "namespace_exists": paths.namespace_dir(product.namespace).is_dir(),
                "product_exists": product.dir.is_dir(),
                "already_bound": bool(coordinates)
                and filing.binds_exactly(product, source, coordinates),
                "defaults_applied": proposal.get("defaults_applied") or [],
                "inherited": proposal.get("inherited") or [],
                "problems": problems,
            }
        )
        return EXIT_OK

    if problems:
        raise TicketError(problems[0], EXIT_ERROR, "\n".join(problems[1:]))

    layout.stamp_current()
    result = module.init(
        sources.provider_context(source, product, coordinates=coordinates), args.extra
    )

    bindings.write(source, product, coordinates)
    product.dir.mkdir(parents=True, exist_ok=True)

    # A source becoming usable is not a decision to make it the default: an
    # init that silently repointed `default_source` would move every bare id.
    if config.load_root().get("default_source") is None:
        config.set_default_source(source)
        result["default_source_set_to"] = source

    merged, origins = config.effective(product.namespace, product.name)
    result.setdefault("source", source)
    result.update(
        {
            "product": product.ref,
            "coordinates": coordinates,
            "defaults_applied": proposal.get("defaults_applied") or [],
            "inherited": proposal.get("inherited") or [],
            "namespace_config": str(paths.level_config_path(product.namespace)),
            "product_config": str(
                paths.level_config_path(product.namespace, product.name)
            ),
            "config": config.redact(merged),
            "config_sources": origins,
        }
    )
    emit(result)
    return EXIT_OK


def verb_fetch(args: argparse.Namespace) -> int:
    target = locate(args)
    location = target.location
    module = provider_for(location.source, "fetch")

    ctx = ticket_context(location, target.address)
    if not sources.is_usable(location.source, ctx["coordinates"]):
        raise TicketError(
            f"'{location.source}' is not bound for {location.product.ref}",
            EXIT_ERROR,
            f"Run `/ticket-init {location.source} --in {location.product.ref}` first.",
        )

    layout.stamp_current()
    (location.dir / "raw").mkdir(parents=True, exist_ok=True)

    result = module.fetch(ctx, args.extra)
    result.update(location_report(target))
    result["paths"] = location.paths()
    result["ticket_json"] = tickets.load(location)

    # Only the fetch can say where a ticket really lives — an Azure DevOps id
    # names no project — so a filing it contradicts is caught here, after it.
    misfiled = filing.misfiling(
        location, result["ticket_json"].get("coordinates") or {}
    )
    if misfiled:
        result["misfiled"] = misfiled

    emit(result)
    return EXIT_OK


def verb_new(args: argparse.Namespace) -> int:
    layout.require_current()
    restrict, context = restrict_of(args), context_of(args)
    sources.require_sources()
    source = args.source or sources.default_source_for(restrict, context)
    sources.require_installed(
        source, "--source names" if args.source else "default_source is"
    )
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

    choice = filing.choose(source, restrict=restrict, context=context, cwd=Path.cwd())
    location = Location(choice.product, source, ticket_id)

    if args.propose:
        emit(
            {
                **location_report(sources.Target(location, filed=False, filing=choice)),
                "exists": location.dir.exists(),
                "elsewhere": [
                    other.qualified
                    for other in layout.locations(source, ticket_id)
                    if other != location
                ],
            }
        )
        return EXIT_OK

    if location.dir.exists():
        raise TicketError(
            f"{location.qualified} already exists",
            EXIT_ERROR,
            f"Pass a different --id, or open {location.dir}.",
        )

    layout.stamp_current()
    ctx = sources.provider_context(source, location.product, location)
    result = module.new(ctx, args.title, args.type, args.extra)
    result.update(location_report(sources.Target(location, filed=False, filing=choice)))
    result["paths"] = location.paths()
    result["ticket_json"] = tickets.load(location)
    emit(result)
    return EXIT_OK


def verb_publish(args: argparse.Namespace) -> int:
    location = require_filed(locate(args))
    module = provider_for(location.source, "publish")

    # Neither Python nor a quoted shell argument expands a leading ~.
    comment_path = Path(args.file).expanduser()
    if not comment_path.is_file():
        raise TicketError(f"comment file not found: {comment_path}", EXIT_NOT_FOUND)

    text = comment_path.read_text(encoding="utf-8").strip()
    if not text:
        raise TicketError(f"comment file is empty: {comment_path}", EXIT_ERROR)

    result = module.publish(ticket_context(location), text, args.extra)
    result.setdefault("source", location.source)
    result.setdefault("id", location.id)
    result["qualified_ref"] = location.qualified

    if args.delete_after_post:
        comment_path.unlink()
        result["deleted"] = str(comment_path)

    emit(result)
    return EXIT_OK


def verb_drift(args: argparse.Namespace) -> int:
    location = require_filed(locate(args))
    module = provider_for(location.source, "drift")

    result = module.drift(ticket_context(location), args.extra)
    result.setdefault("source", location.source)
    result.setdefault("id", location.id)
    result["qualified_ref"] = location.qualified
    emit(result)

    from ticketlib.errors import EXIT_DRIFTED

    return EXIT_DRIFTED if result.get("is_stale") else EXIT_OK


def verb_move(args: argparse.Namespace) -> int:
    location = require_filed(locate(args))
    emit(moves.move(location, layout.parse_product(args.to), args.dry_run))
    return EXIT_OK


def verb_auth_status(args: argparse.Namespace) -> int:
    """
    Each source's credential state, once per credential rather than once per product.

    Products in one namespace share their namespace-level coordinate, which
    is what a credential is keyed by; listing each would repeat one status.
    """
    layout.require_current()
    restrict = restrict_of(args)
    names = [args.source] if args.source else providers.list_sources()
    statuses = []

    for source in names:
        sources.require_installed(source, "--source names")
        module = providers.load_module(source)

        if not providers.coordinates(source):
            status = module.auth_status(sources.provider_context(source, None))
            status.setdefault("source", source)
            status["initialized"] = True
            statuses.append(status)
            continue

        by_key: dict[str, list[Product]] = {}
        for product in layout.products():
            if restrict and not restrict.contains(product):
                continue
            binding = config.binding(source, product.namespace, product.name)
            if sources.is_usable(source, binding):
                key = providers.credential_key(source, binding) or product.ref
                by_key.setdefault(key, []).append(product)

        if not by_key:
            statuses.append(
                {
                    "source": source,
                    "initialized": False,
                    "hint": f"Run `/ticket-init {source}` to bind it.",
                }
            )
            continue

        for bound in by_key.values():
            status = module.auth_status(sources.provider_context(source, bound[0]))
            status.setdefault("source", source)
            status["initialized"] = True
            status["products"] = [product.ref for product in bound]
            statuses.append(status)

    emit({"sources": statuses})
    return EXIT_OK


def verb_scan_roots(args: argparse.Namespace) -> int:
    layout.require_current()
    scope = restrict_of(args)
    namespace, product = (scope.namespace, scope.product) if scope else (None, None)

    if args.set is not None:
        if scope:
            directory = (
                paths.product_dir(scope.namespace, scope.product)
                if scope.product
                else paths.namespace_dir(scope.namespace)
            )
            if not directory.is_dir():
                raise TicketError(
                    f"{scope.ref} does not exist",
                    EXIT_NOT_FOUND,
                    f"Create it with `/ticket-init --in {scope.ref}` first.",
                )
        layout.stamp_current()
        config.set_scan_roots(normalize_directories(args.set), namespace, product)

    effective, origin = config.scan_roots(namespace, product)
    emit(
        {
            "level": scope.ref if scope else "root",
            "level_config": str(paths.level_config_path(namespace, product)),
            "own": config.own_scan_roots(namespace, product),
            "scan_roots": effective,
            "scan_roots_from": origin,
        }
    )
    return EXIT_OK


def normalize_directories(raw: list[str]) -> list[str]:
    """
    Absolute, existing, and each listed once, in the order given.

    Every path is checked before anything is written, so one typo cannot leave
    the stored list half-replaced.
    """
    directories: list[str] = []
    seen: set[str] = set()

    for entry in raw:
        path = Path(entry).expanduser().resolve()
        if not path.is_dir():
            raise TicketError(
                f"not a directory — {path}",
                EXIT_ERROR,
                "Pass only directories that exist. Nothing was saved.",
            )

        # Windows paths compare case-insensitively; normcase is identity elsewhere.
        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            directories.append(str(path))

    return directories


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
    "namespaces": verb_namespaces,
    "defaults": verb_defaults,
    "migrate": verb_migrate,
    "init": verb_init,
    "fetch": verb_fetch,
    "new": verb_new,
    "publish": verb_publish,
    "drift": verb_drift,
    "move": verb_move,
    "auth-status": verb_auth_status,
    "scan-roots": verb_scan_roots,
}


def add_restrict(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument("--in", dest="within", metavar="NS[/PRODUCT]", help=help_text)


def add_context(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--context",
        metavar="NS[/PRODUCT]",
        help="the session context: preferred when resolving and filing, never required",
    )


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
        help="validate that capabilities, role files and coordinates agree",
    )

    p = sub.add_parser(
        "resolve", help="resolve a reference to a location, paths and config"
    )
    p.add_argument(
        "ref", nargs="?", help="[namespace/product/][source:]id, or a web address"
    )
    p.add_argument("--source")
    p.add_argument("--type", help="override the ticket type and record it")
    p.add_argument(
        "--require",
        help="comma-separated: " + ", ".join(sources.REQUIREMENTS),
    )
    add_restrict(p, "only look in, and only file under, this namespace or product")
    add_context(p)

    p = sub.add_parser("list", help="every ticket on disk, newest first")
    add_restrict(p, "only this namespace or product")
    add_context(p)

    p = sub.add_parser(
        "namespaces", help="every namespace and product, with their bindings"
    )
    add_restrict(
        p, "one namespace or product's effective config, and where each value came from"
    )

    p = sub.add_parser(
        "defaults", help="show or set the default namespace and products"
    )
    p.add_argument(
        "--namespace", help="the root default namespace; `default` unsets it"
    )
    p.add_argument(
        "--product",
        metavar="NS/PRODUCT",
        help="that namespace's default product; NS/default unsets it",
    )

    p = sub.add_parser(
        "migrate", help="bring older layouts on disk up to the current one"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would happen, change nothing",
    )
    p.add_argument(
        "--map",
        action="append",
        metavar="SOURCE=NS/PRODUCT",
        help="file every ticket of this source under this product",
    )

    p = sub.add_parser(
        "init", help="bind a source under a product, or create a namespace or product"
    )
    p.add_argument("--source")
    add_restrict(p, "the product to bind under, or the namespace or product to create")
    p.add_argument(
        "--propose",
        action="store_true",
        help="report the binding and where it would be filed; write and validate nothing",
    )

    p = sub.add_parser("fetch", help="refresh the local snapshot (remote sources)")
    p.add_argument("ref")
    p.add_argument("--source")
    add_restrict(p, "only look in, and only file under, this namespace or product")
    add_context(p)

    p = sub.add_parser("new", help="create a ticket in a store that supports it")
    p.add_argument("--source")
    p.add_argument("--title", required=True)
    p.add_argument(
        "--id", help="the slug or id to use; derived from the title if absent"
    )
    p.add_argument("--type")
    p.add_argument(
        "--propose",
        action="store_true",
        help="report where it would be filed and whether the id is taken; create nothing",
    )
    add_restrict(p, "file it under this namespace or product")
    add_context(p)

    p = sub.add_parser("publish", help="post a refinement summary back to the source")
    p.add_argument("ref")
    p.add_argument("--source")
    p.add_argument("--file", required=True)
    p.add_argument("--delete-after-post", action="store_true")
    add_restrict(p, "only look in this namespace or product")
    add_context(p)

    p = sub.add_parser("drift", help="has the ticket moved since it was fetched?")
    p.add_argument("ref")
    p.add_argument("--source")
    add_restrict(p, "only look in this namespace or product")
    add_context(p)

    p = sub.add_parser("move", help="re-file a ticket under another product")
    p.add_argument("ref")
    p.add_argument("--source")
    p.add_argument("--to", required=True, metavar="NS/PRODUCT")
    p.add_argument(
        "--dry-run", action="store_true", help="report what would change, move nothing"
    )
    add_restrict(p, "only look in this namespace or product")
    add_context(p)

    p = sub.add_parser("auth-status", help="report each source's credential state")
    p.add_argument("--source")
    add_restrict(p, "only the bindings in this namespace or product")

    p = sub.add_parser(
        "scan-roots", help="show or replace the default scan roots at one level"
    )
    add_restrict(
        p,
        "the namespace or product whose scan roots to show or set; the root when absent",
    )
    p.add_argument(
        "--set",
        nargs="*",
        metavar="DIR",
        help="replace the list with these directories; none empties it",
    )

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
