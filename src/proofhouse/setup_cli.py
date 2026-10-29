"""`proofhouse setup`: what this machine has, what is missing, and the tools you say you have."""

from __future__ import annotations

import argparse
import json
import sys

from . import setup_check

EXIT_OK = 0
EXIT_USAGE = 2


def _fail(exc: Exception) -> int:
    print(f"error: {exc}", file=sys.stderr)
    return EXIT_USAGE


def _cmd_setup(args: argparse.Namespace) -> int:
    try:
        report = setup_check.build_report(setup_check.SystemProbe())
    except setup_check.SetupError as exc:
        return _fail(exc)
    print(json.dumps(report.to_dict(), indent=2) if args.json else setup_check.render(report))
    return EXIT_OK


def _cmd_add(args: argparse.Namespace) -> int:
    makes = tuple(part.strip() for part in (args.makes or "").split(",") if part.strip())
    try:
        path = setup_check.add_tool(id=args.id, name=args.name, how=args.how, command=args.command, url=args.url,
                                    makes=makes, steps=tuple(args.step or ()))
    except setup_check.SetupError as exc:
        return _fail(exc)
    print(f"saved {args.id} in {path}")
    return EXIT_OK


def _cmd_remove(args: argparse.Namespace) -> int:
    try:
        setup_check.remove_tool(args.id)
    except setup_check.SetupError as exc:
        return _fail(exc)
    print(f"removed {args.id}")
    return EXIT_OK


def add_setup_commands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("setup", help="Find the tools, keys and model servers you have, and what each missing piece would unlock.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_setup)
    sub = p.add_subparsers(dest="setup_command")
    p_add = sub.add_parser("add", help="Tell Proofhouse about a tool it could not find (a program, or a website you drive by hand).")
    p_add.add_argument("id")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--how", required=True, choices=setup_check.HOWS, help="cli: a program on this machine. web: a website.")
    p_add.add_argument("--command", default=None, help="For cli: the program's name as you type it in a terminal.")
    p_add.add_argument("--url", default=None, help="For web: the https address.")
    p_add.add_argument("--makes", default=None, help="Comma list from: image, video, speech, music.")
    p_add.add_argument("--step", action="append", help="One step of using it by hand; repeat for each step.")
    p_add.set_defaults(func=_cmd_add)
    p_remove = sub.add_parser("remove", help="Forget a tool you declared.")
    p_remove.add_argument("id")
    p_remove.set_defaults(func=_cmd_remove)
