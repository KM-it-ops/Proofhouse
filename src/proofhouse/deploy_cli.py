"""`proofhouse deploy FOLDER --to TARGET`: put a finished site online with the hosting service's own tool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import deploy

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAILED = 7


def _cmd_deploy(args: argparse.Namespace) -> int:
    if args.list:
        try:
            targets = deploy.all_targets()
        except deploy.DeployError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        for target in targets.values():
            print(f"{target['id']:<12} {target.get('name', target['id']):<18} {' '.join(target['command'])}")
        return EXIT_OK
    if not args.folder or not args.to:
        print("error: name the folder and where it goes: proofhouse deploy FOLDER --to TARGET (see --list)", file=sys.stderr)
        return EXIT_USAGE
    try:
        done = deploy.deploy(Path(args.folder), args.to, name=args.name, dry_run=args.dry_run)
    except (deploy.DeployError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        print(json.dumps({"target": done.target, "folder": done.folder, "command": done.command, "status": done.status,
                          "url": done.url}, sort_keys=True))
    elif done.status == "dry run":
        print(" ".join(done.command))
    elif done.status == "deployed":
        print(done.url or f"deployed with {done.target}; the tool printed no address")
    else:
        print(done.output, file=sys.stderr)
        print(f"{done.target} failed; nothing else was tried", file=sys.stderr)
    return EXIT_OK if done.status in ("deployed", "dry run") else EXIT_FAILED


def add_deploy_commands(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("deploy", help="Put a finished site online with Netlify, Vercel, Cloudflare Pages, Surge or any tool you add.")
    p.add_argument("folder", nargs="?", help="The site folder (or a make folder holding site/).")
    p.add_argument("--to", default=None, help="Deploy target id (see --list).")
    p.add_argument("--name", default=None, help="Project or subdomain name where the target needs one.")
    p.add_argument("--dry-run", action="store_true", help="Print the exact command and run nothing.")
    p.add_argument("--list", action="store_true", help="List deploy targets.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_deploy)
