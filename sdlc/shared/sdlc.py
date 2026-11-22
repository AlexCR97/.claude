#!/usr/bin/env python3
"""
The command every sdlc skill invokes, so a skill's instructions name one command.

Usage:
    python sdlc.py resolve [<ref>] [--new --title "..."] [--context namespace[/product]]
                           [--coordinate name=value ...]
    python sdlc.py effect <script> [--context namespace[/product]]
    python sdlc.py fetch <ref> [--context namespace[/product]] [--coordinate name=value ...]

Exit codes:
    0  ok
    1  error
    3  ambiguous
    5  not found upstream
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# A Windows console defaults to a legacy codepage, which turns any non-ASCII
# character in a title or an error into mojibake.
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")

from sdlclib import config as configuration
from sdlclib import effect, fetch, layout, resolve
from sdlclib.errors import EXIT_OK, SdlcError


def emit(data: dict) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def verb_resolve(args: argparse.Namespace) -> int:
    emit(
        resolve.resolve(
            args.ref, args.new, args.title, args.context, args.coordinate, Path.cwd()
        )
    )
    return EXIT_OK


def verb_effect(args: argparse.Namespace) -> int:
    script = Path(args.script).expanduser()
    if not script.is_file():
        raise SdlcError(f"script not found: {script}")
    config = configuration.load()
    context = layout.parse_scope(args.context) if args.context else None
    effective = config.effective(
        context.namespace if context else config.default_namespace(),
        context.product if context else None,
    )
    report = effect.check(script, effective.get("sensitive", [])).as_dict()
    report["file"] = str(script)
    emit(report)
    return EXIT_OK


def verb_fetch(args: argparse.Namespace) -> int:
    emit(fetch.fetch(args.ref, args.coordinate, args.context, Path.cwd()))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sdlc.py", description=__doc__)
    verbs = parser.add_subparsers(dest="verb", required=True)

    resolving = verbs.add_parser(
        "resolve", help="report where a ticket lives or would be filed"
    )
    resolving.add_argument("ref", nargs="?")
    resolving.add_argument(
        "--new",
        action="store_true",
        help="report where a new local ticket would be filed",
    )
    resolving.add_argument("--title", help="the new ticket's title")
    resolving.add_argument(
        "--context",
        help="the session's namespace[/product]; it prefers, and never moves a filed ticket",
    )
    resolving.add_argument(
        "--coordinate",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="where the ticket lives upstream, once per coordinate",
    )
    resolving.set_defaults(handler=verb_resolve)

    effecting = verbs.add_parser(
        "effect", help="report whether a script may run without asking"
    )
    effecting.add_argument("script")
    effecting.add_argument(
        "--context",
        help="the ticket's namespace[/product], whose `sensitive` targets apply",
    )
    effecting.set_defaults(handler=verb_effect)

    fetching = verbs.add_parser(
        "fetch", help="mirror a ticket from its source into the ticket's raw/ directory"
    )
    fetching.add_argument(
        "ref", help="a reference that names its source, as github:1234"
    )
    fetching.add_argument(
        "--context",
        help="the session's namespace[/product]; it prefers, and never moves a filed ticket",
    )
    fetching.add_argument(
        "--coordinate",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="where the ticket lives upstream, once per coordinate",
    )
    fetching.set_defaults(handler=verb_fetch)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except SdlcError as error:
        print(f"ERROR: {error.message}", file=sys.stderr)
        if error.hint:
            print(f"HINT: {error.hint}", file=sys.stderr)
        return error.code


if __name__ == "__main__":
    sys.exit(main())
