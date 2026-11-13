"""`proofhouse connect`: put Proofhouse inside the AI apps already on this machine, in one step.

For each app it finds (Claude Code, Cursor, Codex, or one you declared), it registers the Proofhouse tools
(`proofhouse mcp`), installs the Proofhouse skill where the app has a skills folder, and declares each logged-in
command-line agent as a provider so the app's own model does the writing. It keeps a record of exactly what it
did; `proofhouse connect --undo` removes those things and nothing else.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import agent_server, hosts, providers, setup_check
from .optimize import install_skill

SERVER_NAME = "proofhouse"
RECORD_FILE = "connect.json"
# Apps that keep their user-level tool list behind their own command, not a file Proofhouse may edit.
BY_COMMAND: dict[str, dict[str, list[str]]] = {
    "claude": {
        "add": ["claude", "mcp", "add", "--scope", "user", SERVER_NAME, "--"],
        "remove": ["claude", "mcp", "remove", "--scope", "user", SERVER_NAME],
    },
}

Which = Callable[[str], str | None]
Run = Callable[[list[str]], tuple[int, str]]


def _run(argv: list[str]) -> tuple[int, str]:
    program = shutil.which(argv[0]) or argv[0]
    try:
        done = subprocess.run([program, *argv[1:]], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return done.returncode, (done.stdout + done.stderr).strip()


def _record_path() -> Path:
    return providers.proofhouse_home() / RECORD_FILE


def _load_record() -> dict[str, Any]:
    try:
        data = json.loads(_record_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"apps": {}, "providers": {}}
    apps = data.get("apps") if isinstance(data, dict) else None
    made = data.get("providers") if isinstance(data, dict) else None
    return {"apps": apps if isinstance(apps, dict) else {}, "providers": made if isinstance(made, dict) else {}}


def _save_record(record: dict[str, Any]) -> None:
    path = _record_path()
    if not record["apps"] and not record["providers"]:
        path.unlink(missing_ok=True)
        return
    providers.write_atomic(path, json.dumps(record, indent=2, sort_keys=True) + "\n")


def apps_here(which: Which = shutil.which) -> list[tuple[str, str]]:
    """(id, name) of each AI app on this machine that has a place for tools Proofhouse can reach."""
    known = hosts.all_hosts()
    found = []
    try:
        yours = setup_check.load_user().get("tools", [])
    except setup_check.SetupError:
        yours = []
    tools = [*setup_check._shipped().get("agents", []), *yours]
    for tool in tools:
        app = tool.get("id")
        programs = tool.get("programs") or ([tool["command"]] if tool.get("command") else [])
        spec = (known.get(app) or {}).get("mcp") or {}
        reachable = app in BY_COMMAND or spec.get("user")
        if reachable and any(which(str(p)) for p in programs) and app not in [a for a, _ in found]:
            found.append((app, str(tool.get("name") or app)))
    return found


def _declare_agents(record: dict[str, Any], which: Which) -> list[str]:
    """Declare each installed command-line agent as the provider ``agent-<name>``. Returns the agents usable now."""
    data = providers.load_user()
    usable, changed = [], False
    for name, entry in agent_server.load_agents().items():
        argv = entry.get("argv") or [""]
        if not which(str(argv[0])) or not entry.get("port"):
            continue
        provider_id = f"agent-{name}"
        usable.append(name)
        if providers.find(provider_id) is not None:
            continue  # yours already; left alone and not recorded, so --undo will not touch it
        raw = {"id": provider_id, "name": f"{name} (your logged-in agent)",
               "base_url": f"http://{agent_server.HOST}:{entry['port']}/v1", "shape": "openai-compatible",
               "key_env": agent_server.TOKEN_ENV}
        providers.parse_provider(raw, "yours")
        data["providers"] = [p for p in data["providers"] if p.get("id") != provider_id] + [raw]
        record["providers"][provider_id] = raw
        changed = True
    if changed:
        providers.save_user(data)
    return usable


def _server_entry(app: str, agents: list[str], which: Which) -> dict[str, Any]:
    args = ["mcp"] + (["--agent", app] if app in agents else [])
    return {"command": which("proofhouse") or "proofhouse", "args": args}


def connect(*, which: Which = shutil.which, run: Run = _run, say: Callable[[str], None] = print) -> int:
    apps = apps_here(which)
    if not apps:
        say("No AI app was found on this machine (looked for Claude Code, Cursor and Codex on your PATH).\n"
            "Install one, or tell Proofhouse about yours with `proofhouse setup add`, then run this again.\n"
            "Proofhouse still works from the command line: `proofhouse demo make` shows a whole make.")
        return 1
    record = _load_record()
    try:
        agents = _declare_agents(record, which)
    except providers.ProviderError as exc:
        say(f"Could not declare your logged-in agents as providers: {exc}")
        return 1
    problems = 0
    for app, name in apps:
        done = record["apps"].setdefault(app, {})
        entry = _server_entry(app, agents, which)
        say(f"{name}:")
        if app in BY_COMMAND:
            code, text = run([*BY_COMMAND[app]["add"], entry["command"], *entry["args"]])
            if code == 0:
                done["tools"] = "command"
                say("  tools registered for every project (through its own `mcp add` command)")
            elif "already exists" in text.lower():
                say("  tools: it already has a server named proofhouse; left as it is")
            else:
                problems += 1
                say(f"  tools NOT registered: {text or 'its command failed'}")
        else:
            try:
                target = hosts.target(app, "mcp", SERVER_NAME, None)
                result = hosts.install(target, entry)
                if result.startswith("installed"):
                    done["tools"] = "file"
                say(f"  tools: {result}")
            except hosts.HostError as exc:
                problems += 1
                say(f"  tools NOT registered: {exc}")
        say("  " + _skill(app, name, done))
        if not done:
            record["apps"].pop(app, None)
    _save_record(record)
    say("")
    if agents:
        judge = f", and {agents[1]} judges it" if len(agents) > 1 else ""
        say(f"Writing is done by your logged-in {agents[0]}{judge}: no key to paste, nothing metered by Proofhouse.")
    else:
        say("No logged-in command-line agent (claude, codex, grok) was found, so a make from chat needs a provider and\n"
            "a model named in the request, for example a model on this machine through Ollama.")
    say("Next: open a NEW chat in the app and say: Proofhouse, make me a skill that ...\n"
        "It asks its questions in the chat, reads back what it understood, and makes it once you say yes.\n"
        "To take all of this out again: proofhouse connect --undo")
    return 1 if problems else 0


def _skill(app: str, name: str, done: dict[str, Any]) -> str:
    from .learn_catalog import skill_hosts

    if app not in skill_hosts():
        return f"skill: {name} has no skills folder Proofhouse knows; the tools above are enough"
    try:
        result = install_skill.install(host=app)
    except install_skill.InstallSkillError as exc:
        if "already exists" in str(exc):
            return "skill: one named proofhouse is already there; left as it is"
        return f"skill NOT installed: {exc}"
    done["skill"] = result.name
    return f"skill installed: {result.dest}"


def undo(*, run: Run = _run, say: Callable[[str], None] = print) -> int:
    record = _load_record()
    if not record["apps"] and not record["providers"]:
        say("Nothing to undo: `proofhouse connect` has not changed anything on this machine.")
        return 0
    names = {tool.get("id"): tool.get("name") for tool in setup_check._shipped().get("agents", [])}
    problems = 0
    for app in list(record["apps"]):
        done = record["apps"][app]
        say(f"{names.get(app) or app}:")
        how = done.get("tools")
        if how == "command":
            code, text = run(BY_COMMAND[app]["remove"])
            if code == 0 or "no mcp server" in text.lower() or "not found" in text.lower():
                done.pop("tools")
                say("  tools removed")
            else:
                problems += 1
                say(f"  tools NOT removed: {text or 'its command failed'}")
        elif how == "file":
            try:
                say("  tools: " + hosts.uninstall(hosts.target(app, "mcp", SERVER_NAME, None)))
                done.pop("tools")
            except hosts.HostError as exc:
                problems += 1
                say(f"  tools NOT removed: {exc}")
        if done.get("skill"):
            try:
                install_skill.uninstall(done["skill"], host=app)
                done.pop("skill")
                say("  skill removed")
            except install_skill.InstallSkillError as exc:
                problems += 1
                say(f"  skill NOT removed: {exc}")
        if not done:
            record["apps"].pop(app)
    try:
        data = providers.load_user()
        kept = [p for p in data["providers"] if record["providers"].get(p.get("id")) != p]
        if len(kept) != len(data["providers"]):
            data["providers"] = kept
            providers.save_user(data)
        record["providers"] = {}
    except providers.ProviderError as exc:
        problems += 1
        say(f"Providers NOT removed: {exc}")
    _save_record(record)
    say("" if problems else "\nEverything `proofhouse connect` added is gone. Your makes and their records are untouched.")
    return 1 if problems else 0


def _cmd_connect(args: argparse.Namespace) -> int:
    return undo() if args.undo else connect()


def add_connect_command(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "connect", help="Put Proofhouse inside the AI apps on this machine (Claude Code, Cursor, Codex): registers "
                        "its tools and skill so you can make things from the app's chat. --undo takes it out.")
    p.add_argument("--undo", action="store_true", help="Remove exactly what connect added, and nothing else.")
    p.set_defaults(func=_cmd_connect)
