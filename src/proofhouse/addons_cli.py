"""`proofhouse addons list|install|remove`: plug in other people's providers, services, tools and make kinds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import addons

EXIT_OK = 0
EXIT_USAGE = 2


def _cmd_list(args: argparse.Namespace) -> int:
    found, broken = addons.all_addons()
    if args.json:
        print(json.dumps({"addons": [{"name": a.name, "version": a.version, "origin": a.origin, "description": a.description,
                                      "adds": a.counts()} for a in found], "broken": broken}, sort_keys=True))
        return EXIT_OK
    for addon in found:
        adds = ", ".join(f"{n} {section.replace('_', ' ')}" for section, n in addon.counts().items()) or "nothing"
        print(f"{addon.name:<20} {addon.version:<8} {addon.origin:<8} adds {adds}  {addon.description}")
    if not found:
        print("no add-ons yet: install a pack with `proofhouse addons install <folder>`, or pip-install a package that provides one")
    for line in broken:
        print(f"skipped: {line}", file=sys.stderr)
    return EXIT_OK


def _cmd_install(args: argparse.Namespace) -> int:
    try:
        addon = addons.install(Path(args.source))
    except (addons.AddonError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    adds = ", ".join(f"{n} {section.replace('_', ' ')}" for section, n in addon.counts().items()) or "nothing"
    print(f"installed {addon.name} {addon.version}".rstrip() + f": adds {adds} ({addons.packs_dir() / addon.name})")
    return EXIT_OK


def _cmd_approve(args: argparse.Namespace) -> int:
    from . import learn_catalog
    from .learn import LearnError

    try:
        path = learn_catalog.approve(args.id)
    except LearnError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"approved {args.id} ({path})")
    return EXIT_OK


def _cmd_remove(args: argparse.Namespace) -> int:
    try:
        gone = addons.remove(args.name)
    except (addons.AddonError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"removed {args.name} ({gone})")
    return EXIT_OK


def add_addon_commands(subparsers: argparse._SubParsersAction) -> None:
    p_addons = subparsers.add_parser("addons", help="Add-ons: other people's providers, services, tools and make kinds.")
    sub = p_addons.add_subparsers(dest="addons_command", required=True)
    p = sub.add_parser("list", help="Every add-on, what it adds, and any that could not be loaded.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_list)
    p = sub.add_parser("install", help="Check an add-on pack (a folder with addon.json) and install it.")
    p.add_argument("source", help="The pack's folder, or its addon.json.")
    p.set_defaults(func=_cmd_install)
    p = sub.add_parser("remove", help="Remove an installed add-on pack.")
    p.add_argument("name")
    p.set_defaults(func=_cmd_remove)
    p = sub.add_parser("approve", help="Approve a learned entry that sends a key or runs a command.")
    p.add_argument("pack", choices=["learned"])
    p.add_argument("id", help="Entry id in the learned pack.")
    p.set_defaults(func=_cmd_approve)
