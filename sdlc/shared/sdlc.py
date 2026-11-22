#!/usr/bin/env python3
"""
The command every sdlc skill invokes, so a skill's instructions name one command.

Usage:
    python sdlc.py resolve [<ref>] [--new --title "..."] [--context namespace[/product]]
                           [--coordinate name=value ...]

Exit codes:
    0  ok
    1  error
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

from sdlclib import resolve
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
