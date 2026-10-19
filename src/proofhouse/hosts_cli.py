"""`proofhouse hosts list`, `proofhouse install agent|rule|mcp`, `proofhouse uninstall agent|rule|mcp`."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import hosts

EXIT_OK = 0
EXIT_USAGE = 2


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _frontmatter_value(text: str, key: str) -> str | None:
    match = re.match(r"---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        return None
    for line in match.group(1).splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip() or None
    return None


def _cmd_hosts_list(args: argparse.Namespace) -> int:
    try:
        found = hosts.all_hosts()
    except hosts.HostError as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps({"hosts": list(found.values())}, sort_keys=True))
        return EXIT_OK
    for host in found.values():
        kinds = []
        for kind in hosts.KINDS:
            spec = host.get(kind)
            if spec:
                where = "+".join(scope for scope in ("user", "project") if scope in spec)
                kinds.append(f"{kind} ({where})")
        print(f"{host['id']:<10} {host.get('name', host['id']):<14} {', '.join(kinds) or '-'}")
        if isinstance(host.get("note"), str):
            print(f"{'':<10} {host['note']}")
    print(f"\nAdd any other tool in {hosts.proofhouse_home() / 'hosts.json'} (same shape as the shipped list).")
    return EXIT_OK


def _content(args: argparse.Namespace) -> tuple[str, object]:
    if args.kind == "mcp":
        env = {}
        for pair in args.env or []:
            if "=" not in pair:
                raise hosts.HostError(f"--env {pair!r} must look like NAME=value")
            key, value = pair.split("=", 1)
            env[key] = value
        entry: dict[str, object] = {"command": args.command_line, "args": list(args.arg or [])}
        if env:
            entry["env"] = env
        if not args.command_line:
            raise hosts.HostError("an MCP server needs --command")
        return hosts.check_name(args.source), entry
    text = Path(args.source).read_text(encoding="utf-8")
    if args.kind == "agent":
        name = args.name or _frontmatter_value(text, "name")
        if not name or not _frontmatter_value(text, "description"):
            raise hosts.HostError("an agent file needs frontmatter with name: and description: (or pass --name)")
        return hosts.check_name(name), text
    name = args.name or hosts.check_name(re.sub(r"[^a-z0-9-]+", "-", Path(args.source).stem.lower()).strip("-"))
    return hosts.check_name(name), text


def _cmd_install(args: argparse.Namespace) -> int:
    try:
        name, content = _content(args)
        target = hosts.target(args.into, args.kind, name, Path(args.project) if args.project else None)
        if target.kind == "rule" and target.format == "file" and target.path.suffix == ".mdc" and not str(content).startswith("---"):
            content = f"---\ndescription: {name}\nalwaysApply: true\n---\n{content}"
        print(hosts.install(target, content, force=args.force))
    except (hosts.HostError, OSError) as exc:
        return _fail(str(exc))
    return EXIT_OK


def _cmd_uninstall(args: argparse.Namespace) -> int:
    try:
        target = hosts.target(args.host, args.kind, args.name, Path(args.project) if args.project else None)
        print(hosts.uninstall(target, force=args.force))
    except (hosts.HostError, OSError, ValueError) as exc:
        return _fail(str(exc))
    return EXIT_OK


def add_host_commands(subparsers: argparse._SubParsersAction) -> None:
    p_hosts = subparsers.add_parser("hosts", help="The tools Proofhouse can install into (Claude Code, Cursor, Codex, or any you add).")
    hosts_sub = p_hosts.add_subparsers(dest="hosts_command", required=True)
    p_list = hosts_sub.add_parser("list", help="List tools and what each can take.")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_hosts_list)

    p_install = subparsers.add_parser("install", help="Install an agent, rule or MCP server into a tool you work in.")
    install_sub = p_install.add_subparsers(dest="install_kind", required=True)
    p_uninstall = subparsers.add_parser("uninstall", help="Remove what `proofhouse install` put into a tool.")
    uninstall_sub = p_uninstall.add_subparsers(dest="uninstall_kind", required=True)

    helps = {
        "agent": "A subagent file (Markdown with name: and description: frontmatter).",
        "rule": "A rules file (Markdown) added to the tool's rules.",
        "mcp": "An MCP server, by name, with --command and --arg.",
    }
    for kind in hosts.KINDS:
        p = install_sub.add_parser(kind, help=helps[kind])
        p.add_argument("source", help="The server's name." if kind == "mcp" else "The file to install.")
        p.add_argument("--into", required=True, help="Tool id (see `proofhouse hosts list`).")
        p.add_argument("--project", default=None, help="Install into this project folder instead of your user settings.")
        p.add_argument("--name", default=None, help="Name to install under (default from the file).")
        p.add_argument("--force", action="store_true", help="Replace something Proofhouse did not write (a copy is kept).")
        if kind == "mcp":
            p.add_argument("--command", dest="command_line", default=None, help="Command that starts the server.")
            p.add_argument("--arg", action="append", help="One argument for the command (repeat for more; write --arg=-y for one that starts with a dash).")
            p.add_argument("--env", action="append", help="NAME=value for the server's environment (repeat for more).")
        p.set_defaults(func=_cmd_install, kind=kind)

        u = uninstall_sub.add_parser(kind, help=f"Remove an installed {kind}.")
        u.add_argument("name")
        u.add_argument("--from", dest="host", required=True, help="Tool id.")
        u.add_argument("--project", default=None, help="The project folder it was installed into, if any.")
        u.add_argument("--force", action="store_true", help="Remove it even if it was edited since.")
        u.set_defaults(func=_cmd_uninstall, kind=kind)
