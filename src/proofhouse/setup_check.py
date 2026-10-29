"""`proofhouse setup`: find what this machine has, say what is missing and what it unlocks, and keep the tools you say you have.

Looking never starts a program: it asks the PATH, looks for files, reads environment variable names
and opens a plain connection to this machine's own ports. Keys are reported as set or not set; their
values are never put in the report. What Proofhouse cannot find, you declare with ``add_tool``; it is
kept as data in ``PROOFHOUSE_HOME/tools.json``, the same way providers and media services are.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import re
import shutil
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from . import deploy, media, providers, sitecheck, train

TOOLS_SCHEMA = "proofhouse.tools/v1"
SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "tools.json"
HOWS = ("cli", "web")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_PROGRAM = re.compile(r"[^\s]{1,200}")


class SetupError(ValueError):
    """The tools list cannot be read or changed as asked; nothing was changed."""


class Probe(Protocol):
    def which(self, name: str) -> str | None: ...
    def key_is_set(self, name: str) -> bool: ...
    def answers(self, host: str, port: int) -> bool: ...
    def platform(self) -> tuple[str, str]: ...
    def has_module(self, name: str) -> bool: ...
    def browser(self) -> str | None: ...


class SystemProbe:
    """This machine, asked without starting anything."""

    def which(self, name: str) -> str | None:
        return shutil.which(name)

    def key_is_set(self, name: str) -> bool:
        return bool(os.environ.get(name))

    def answers(self, host: str, port: int) -> bool:
        try:
            socket.create_connection((host, port), timeout=0.4).close()
        except OSError:
            return False
        return True

    def platform(self) -> tuple[str, str]:
        return platform.system(), platform.machine()

    def has_module(self, name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            return False

    def browser(self) -> str | None:
        return sitecheck.find_browser()


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    kind: str  # agent, system or hosting
    found: bool
    unlocks: str
    get: str


@dataclass(frozen=True)
class Key:
    env: str
    is_set: bool
    used_by: tuple[str, ...]
    roles: frozenset[str]  # model, media, train, host


@dataclass(frozen=True)
class Server:
    id: str
    name: str
    port: int
    installed: bool
    answering: bool
    start: str
    get: str


@dataclass(frozen=True)
class Declared:
    id: str
    name: str
    how: str
    found: bool
    makes: tuple[str, ...]
    url: str
    command: str
    steps: tuple[str, ...]

    @property
    def hand_driven(self) -> bool:
        return self.how == "web"


@dataclass(frozen=True)
class Ability:
    id: str
    title: str
    ok: bool
    using: str = ""
    get: str = ""
    note: str = ""


@dataclass
class Report:
    system: str = ""
    tools: list[Tool] = field(default_factory=list)
    keys: list[Key] = field(default_factory=list)
    servers: list[Server] = field(default_factory=list)
    declared: list[Declared] = field(default_factory=list)
    abilities: list[Ability] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "tools": [{"id": t.id, "name": t.name, "kind": t.kind, "found": t.found, "unlocks": t.unlocks, "get": t.get} for t in self.tools],
            "keys": [{"env": k.env, "set": k.is_set, "used_by": list(k.used_by)} for k in self.keys],
            "servers": [{"id": s.id, "name": s.name, "port": s.port, "installed": s.installed, "answering": s.answering} for s in self.servers],
            "declared": [{"id": d.id, "name": d.name, "how": d.how, "found": d.found, "makes": list(d.makes), "url": d.url,
                          "command": d.command, "steps": list(d.steps)} for d in self.declared],
            "abilities": [{"id": a.id, "title": a.title, "ok": a.ok, "using": a.using, "get": a.get, "note": a.note} for a in self.abilities],
        }


def user_path() -> Path:
    return providers.proofhouse_home() / "tools.json"


def _shipped() -> dict[str, Any]:
    return json.loads(SHIPPED_PATH.read_text(encoding="utf-8"))


def load_user() -> dict[str, Any]:
    """Your tools file as data ({"tools": [...]}); empty when there is none."""
    path = user_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema": TOOLS_SCHEMA, "tools": []}
    except (OSError, ValueError) as exc:
        raise SetupError(f"{path} is unreadable: {type(exc).__name__}; fix or remove it") from None
    if not isinstance(data, dict) or data.get("schema") != TOOLS_SCHEMA or not isinstance(data.get("tools"), list):
        raise SetupError(f"{path} is unreadable as a tools file (expected schema {TOOLS_SCHEMA} and a tools list); fix or remove it")
    for raw in data["tools"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or raw.get("how") not in HOWS:
            raise SetupError(f"{path} is unreadable: it has an entry that is not a declared tool; fix or remove it")
    return data


def _save(data: dict[str, Any]) -> None:
    path = user_path()
    try:
        providers.write_atomic(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        raise SetupError(f"could not save {path}: {exc}; it is unchanged") from None


def add_tool(*, id: str, name: str, how: str, command: str | None = None, url: str | None = None,
             makes: tuple[str, ...] | list[str] = (), steps: tuple[str, ...] | list[str] = ()) -> Path:
    """Say you have a tool. ``cli``: a program Proofhouse finds by name. ``web``: a website you or a browser drive by hand."""
    if not isinstance(id, str) or not _ID.fullmatch(id):
        raise SetupError(f"id {id!r} must be lowercase letters, digits and '-'")
    if not isinstance(name, str) or not name.strip():
        raise SetupError("give the tool a name (--name)")
    if how not in HOWS:
        raise SetupError(f"how must be one of: {', '.join(HOWS)} (cli = a program on this machine, web = a website)")
    bad = [kind for kind in makes if kind not in media.KINDS]
    if bad:
        raise SetupError(f"makes must be some of: {', '.join(media.KINDS)} (not {', '.join(bad)})")
    entry: dict[str, Any] = {"id": id, "name": name.strip(), "how": how, "makes": list(makes), "steps": [s.strip() for s in steps if s.strip()]}
    if how == "cli":
        if not command or not _PROGRAM.fullmatch(command):
            raise SetupError("a command-line tool needs --command: the program's name, as you type it in a terminal")
        entry["command"] = command
    else:
        parsed = urlparse(url or "")
        if parsed.scheme != "https" or not parsed.hostname:
            raise SetupError("a website tool needs --url, an https address")
        entry["url"] = url
    data = load_user()
    data["tools"] = [t for t in data["tools"] if t["id"] != id] + [entry]
    data["schema"] = TOOLS_SCHEMA
    _save(data)
    return user_path()


def remove_tool(id: str) -> None:
    data = load_user()
    kept = [t for t in data["tools"] if t["id"] != id]
    if len(kept) == len(data["tools"]):
        raise SetupError(f"no declared tool named {id!r}; see `proofhouse setup`")
    data["tools"] = kept
    _save(data)


def _any(probe: Probe, programs: list[str]) -> bool:
    return any(probe.which(p) for p in programs)


def build_report(probe: Probe) -> Report:
    shipped = _shipped()
    user = load_user()
    system, machine = probe.platform()
    apple = system == "Darwin" and machine == "arm64"
    report = Report(system=f"{system} {machine}")

    for raw in shipped["agents"]:
        report.tools.append(Tool(raw["id"], raw["name"], "agent", _any(probe, raw["programs"]), raw["unlocks"], raw["get"]))
    for raw in shipped["system"]:
        report.tools.append(Tool(raw["id"], raw["name"], "system", _any(probe, raw["programs"]), raw["unlocks"], raw["get"]))
    report.tools.append(Tool("browser", "Chrome or Edge", "system", probe.browser() is not None,
                             "open sites like a visitor and take desktop and phone screenshots", "install Google Chrome or Microsoft Edge"))
    report.tools.append(Tool("mlx", "MLX (Apple Silicon)", "system", apple and probe.has_module("mlx_lm"),
                             "train a model on this Mac at no cost",
                             "pip install mlx-lm" if apple else "needs an Apple Silicon Mac; not available on this machine"))
    for target in deploy.all_targets().values():
        name = target.get("name", target["id"])
        report.tools.append(Tool(target["id"], name, "hosting", probe.which(target.get("tool") or target["id"]) is not None,
                                 f"put a finished site online with {name}", target.get("install", "")))

    uses: dict[str, list[str]] = {}
    roles: dict[str, set[str]] = {}

    def note(env: str | None, who: str, role: str) -> None:
        if env:
            uses.setdefault(env, []).append(who)
            roles.setdefault(env, set()).add(role)

    for provider in providers.all_providers().values():
        note(provider.key_env, provider.id, "model")
    for service in media.all_media_providers().values():
        note(service.key_env, f"{service.id} (media)", "media")
    for service in train.all_services().values():
        note(service.key_env, f"{service.id} (training)", "train")
    for target in deploy.all_targets().values():
        note(target.get("key_env"), f"{target['id']} (hosting)", "host")
    for env in sorted(uses):
        report.keys.append(Key(env, probe.key_is_set(env), tuple(dict.fromkeys(uses[env])), frozenset(roles[env])))

    for provider in providers.all_providers().values():
        if provider.local:
            parsed = urlparse(provider.base_url)
            info = shipped["servers"].get(provider.id, {})
            port = parsed.port or 80
            report.servers.append(Server(provider.id, provider.name, port, _any(probe, info.get("programs", [])),
                                         probe.answers(parsed.hostname or "localhost", port), info.get("start", ""), info.get("get", "")))

    for raw in user["tools"]:
        found = raw["how"] == "cli" and probe.which(raw.get("command", "")) is not None
        report.declared.append(Declared(raw["id"], raw.get("name", raw["id"]), raw["how"], found, tuple(raw.get("makes", ())),
                                        raw.get("url", ""), raw.get("command", ""), tuple(raw.get("steps", ()))))

    report.abilities = _abilities(report, apple)
    return report


def _abilities(report: Report, apple: bool) -> list[Ability]:
    found = {t.id for t in report.tools if t.found}
    agents = [t.name for t in report.tools if t.kind == "agent" and t.found]
    hosting = [t.name for t in report.tools if t.kind == "hosting" and t.found]
    running = [s.name for s in report.servers if s.answering]

    def keys(role: str) -> list[str]:
        return [k.env for k in report.keys if k.is_set and role in k.roles]

    model_keys, media_keys, train_keys = keys("model"), keys("media"), keys("train")
    media_declared = [d.name for d in report.declared if d.makes and (d.found or d.hand_driven)]
    mac = ["MLX on this Mac"] if "mlx" in found else []
    return [
        Ability("host-check", "Check, record and compare work an agent wrote (no key needed)", True, "built in"),
        Ability("write-with-agent", "Have an agent you already use write the work", bool(agents), ", ".join(agents),
                "install an AI coding agent: Claude Code, Codex, Cursor, Gemini CLI or Grok CLI"),
        Ability("make-with-model", "Make things with a model through Proofhouse", bool(model_keys or running),
                ", ".join(model_keys + running), "set a provider key (for example OPENAI_API_KEY) or start a local model server such as Ollama"),
        Ability("free-local-model", "Run a model on this machine at no cost", bool(running), ", ".join(running),
                "start a local model server: Ollama, LM Studio, vLLM or llama.cpp"),
        Ability("render-video", "Put a finished video together", {"ffmpeg", "ffprobe"} <= found, "ffmpeg and ffprobe",
                "install ffmpeg (it brings ffprobe): https://ffmpeg.org/download.html"),
        Ability("open-sites", "Open a site like a visitor and take screenshots", "browser" in found, "your browser",
                "install Google Chrome or Microsoft Edge"),
        Ability("deploy-site", "Put a finished site online", bool(hosting), ", ".join(hosting),
                "install a hosting tool, for example: npm install -g vercel",
                "Proofhouse cannot see whether you are signed in to it; sign in with the tool first." if hosting else ""),
        Ability("make-media", "Make images, voice, music or video", bool(media_keys or media_declared),
                ", ".join(media_keys + media_declared),
                "set a media service key (for example OPENAI_API_KEY), or tell Proofhouse about a tool you have: proofhouse setup add"),
        Ability("train-model", "Train a model on your own data", bool(train_keys or mac), ", ".join(train_keys + mac),
                "set a training service key (for example TOGETHER_API_KEY), or use an Apple Silicon Mac with mlx-lm"),
    ]


def render(report: Report) -> str:
    lines = [f"Proofhouse setup  ({report.system})", "", "What I found"]
    found = [t for t in report.tools if t.found]
    lines += [f"  found    {t.name}" for t in found] or ["  nothing yet"]
    lines.append("")
    missing = [t for t in report.tools if not t.found]
    if missing:
        lines.append("Not found, and what each unlocks")
        lines += [f"  {t.name}. Unlocks: {t.unlocks}. Get it: {t.get}" for t in missing]
        lines.append("")

    lines.append("Keys (only whether each is set; values are never shown)")
    lines += [f"  {'set    ' if k.is_set else 'not set'}  {k.env}   used by {', '.join(k.used_by)}" for k in report.keys]
    lines.append("")

    lines.append("Model servers on this machine")
    for server in report.servers:
        if server.answering:
            state = "running"
        elif server.installed:
            state = f"installed, not running. Start it: {server.start}" if server.start else "installed, not running"
        else:
            state = f"not installed. Get it: {server.get}" if server.get else "not running"
        lines.append(f"  {server.name} (port {server.port}): {state}")
    lines.append("")

    if report.declared:
        lines.append("Tools you told me about")
        for tool in report.declared:
            makes = f"; makes {', '.join(tool.makes)}" if tool.makes else ""
            if tool.hand_driven:
                lines.append(f"  {tool.name}: a website you use by hand ({tool.url}){makes}")
                lines += [f"      {number}. {step}" for number, step in enumerate(tool.steps, start=1)]
                lines.append("      Then bring the file back: `proofhouse record` keeps it as a version, "
                             "and `proofhouse render video FOLDER` assembles clips into a video.")
            else:
                state = "found" if tool.found else f"not found on this machine (looking for `{tool.command}`)"
                lines.append(f"  {tool.name}: the command `{tool.command}`, {state}{makes}")
        lines.append("")

    lines.append("You can do now")
    for ability in (a for a in report.abilities if a.ok):
        lines.append(f"  - {ability.title}" + (f"   [{ability.using}]" if ability.using else ""))
        if ability.note:
            lines.append(f"      Note: {ability.note}")
    lines += ["", "Not yet"]
    cannot = [a for a in report.abilities if not a.ok]
    if not cannot:
        lines.append("  - nothing; every ability is available")
    for ability in cannot:
        lines += [f"  - {ability.title}", f"      To unlock: {ability.get}"]
    lines += ["", "Tell me about a tool I could not find:  proofhouse setup add ID --name NAME --how cli|web ...",
              "Try now, no key needed:  proofhouse check prompt FILE"]
    return "\n".join(lines)
