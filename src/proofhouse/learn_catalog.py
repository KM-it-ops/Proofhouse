"""Research and learn entries Proofhouse does not know yet (platforms, hosts, deploy targets, media and training services).

Each list uses the same flow as make kinds (``learn.py``): one research call through the spend gate, strict
parse, validate with that list's own checker, save in the ``learned`` add-on pack, then continue. Built-in
and user entries always win over learned ones. Keyed or command-running learned entries need explicit
approval or ``--allow-commands`` before anything runs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import addons, providers
from .learn import LEARNED_PACK, SOURCES_NOTE, LearnError, pack_path

_HOST_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_PLATFORM_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")


@dataclass(frozen=True, slots=True)
class Research:
    provider_id: str
    model: str
    max_cost_usd: str | None = None
    transport: Any = None


def _need_model(what: str) -> LearnError:
    return LearnError(f"a model is needed to research {what}; name --provider and --model")


def _json_blob(answer: str | None) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", answer or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    return data if isinstance(data, dict) else None


def _meta(answer: dict[str, Any], *, learned_by: str) -> dict[str, Any]:
    sources = answer.get("sources") if isinstance(answer.get("sources"), list) else []
    return {
        "what_it_is": str(answer.get("what_it_is", "")).strip()[:600],
        "sources": [s for s in sources if isinstance(s, str) and re.match(r"https?://\S+$", s) and len(s) <= 300][:10],
        "sources_note": SOURCES_NOTE,
        "learned_by": learned_by,
        "learned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _https_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://") and " " not in url


def _pack_raw() -> dict[str, Any]:
    path = pack_path()
    if not path.is_file():
        return {"schema": addons.ADDON_SCHEMA, "name": LEARNED_PACK, "version": "1",
                "description": "Things Proofhouse researched the first time you asked for them"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path.replace(path.with_name(f"addon.json.unreadable-{stamp}"))
        return {"schema": addons.ADDON_SCHEMA, "name": LEARNED_PACK, "version": "1",
                "description": "Things Proofhouse researched the first time you asked for them"}


def _save_section(section: str, entry: dict[str, Any], id_key: str) -> Path:
    from . import app_platforms, deploy, hosts, media, train

    raw = _pack_raw()
    for key in addons.SECTIONS:
        raw.setdefault(key, [])
    entries = [e for e in raw.get(section, []) if e.get(id_key) != entry[id_key]] + [entry]
    raw[section] = entries
    raw["schema"] = addons.ADDON_SCHEMA
    raw["name"] = LEARNED_PACK
    raw.setdefault("version", "1")
    raw.setdefault("description", "Things Proofhouse researched the first time you asked for them")
    addon = addons._check(raw, str(pack_path()), "pack")
    if section == "app_platforms":
        for item in addon.contents["app_platforms"]:
            app_platforms._validate_entry(item, "learned")
    if section == "hosts":
        hosts._check_hosts(addon.contents["hosts"], "learned")
    if section == "deploy_targets":
        for item in addon.contents["deploy_targets"]:
            deploy._check(item, "learned")
    if section == "media_providers":
        for item in addon.contents["media_providers"]:
            media._parse(item, "learned")
    if section == "training_services":
        for item in addon.contents["training_services"]:
            train._parse(item, "learned")
    providers.write_atomic(pack_path(), json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return pack_path()


def learned_raw(section: str, entry_id: str, id_key: str = "id") -> dict[str, Any] | None:
    raw = _pack_raw()
    for entry in raw.get(section, []):
        if isinstance(entry, dict) and entry.get(id_key) == entry_id:
            return entry
    return None


def approve(entry_id: str) -> Path:
    raw = _pack_raw()
    found = False
    for section in addons.SECTIONS:
        items = raw.get(section, [])
        for index, entry in enumerate(items):
            if not isinstance(entry, dict):
                continue
            key = entry.get("kind") if section == "make_kinds" else entry.get("id")
            if key == entry_id:
                items[index] = {**entry, "approved": True}
                found = True
    if not found:
        raise LearnError(f"no learned entry named {entry_id!r}; see `proofhouse addons list`")
    providers.write_atomic(pack_path(), json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return pack_path()


def needs_approval(entry: dict[str, Any]) -> bool:
    return entry.get("approved") is False


def refusal_message(entry: dict[str, Any], *, thing: str, command: str) -> str:
    sources = ", ".join(entry.get("sources") or []) or "none"
    address = entry.get("base_url") or entry.get("command") or entry.get("install")
    return (f"{thing} is not approved yet; nothing was sent to {address}. "
            f"Sources ({entry.get('sources_note', SOURCES_NOTE)}): {sources}. "
            f"After you check them, run: {command}")


APPROVE_CMD = "proofhouse addons approve learned"


def plain_platform_id(text: str) -> str | None:
    name = text.strip().lower()
    return name if _PLATFORM_ID.fullmatch(name) else None


def plain_host_id(text: str) -> str | None:
    name = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return name if _HOST_ID.fullmatch(name) else None


def plain_service_id(text: str) -> str | None:
    name = text.strip().lower()
    return name if providers._ID.fullmatch(name) else None


# --- research prompts ---------------------------------------------------------------------------

_PLATFORM_RESEARCH = (
    "Proofhouse wraps working apps for many platforms. Someone asked for platform {platform_id}, which is not in "
    "Proofhouse yet. Research what that platform needs as a shell around a shared web app: its name, what files and "
    "checks prove the shell is real, and how a contained offline build would run (tool, install hint, command steps, "
    "output path, host_os). Reply with JSON only: "
    '{"what_it_is": "<one or two sentences>", "name": "<display name>", "shell": "<short description>", '
    '"write": "<instructions for the writer model>", "checks": {"files": ["..."], "json": {"file": ["keys"]}, '
    '"site": false}, "build": {"tool": "...", "install": "...", "command": ["..."], "output": "..."}, '
    '"host_os": ["windows"|"macos"|"linux"], "sources": ["https://..."]}'
)

_HOST_RESEARCH = (
    "Proofhouse installs agents, rules and skills into many coding tools and AI workspaces. Someone asked for host "
    "{host_id}, which Proofhouse does not know yet. Research where that tool keeps skills and project rules on disk. "
    "Reply with JSON only: "
    '{"what_it_is": "<one or two sentences>", "name": "<display name>", "skills_folder": "<folder under the home '
    'directory, such as .cursor>", "start_hint": "<where the user starts a session>", '
    '"rule": {"user": "~/.tool/AGENTS.md", "format": "md-block"}, "sources": ["https://..."]}'
)

_DEPLOY_RESEARCH = (
    "Proofhouse deploys finished sites with each hosting service's own command-line tool. Someone asked for deploy "
    "target {target_id}, which Proofhouse does not know yet. Research the official CLI command to publish a folder, "
    "with {{folder}} and {{name}} placeholders. Reply with JSON only: "
    '{"what_it_is": "<one or two sentences>", "name": "<display name>", "tool": "<cli name>", "install": "<how to '
    'install it>", "command": ["words", "{folder}"], "key_env": "<ENV name or omit>", "sources": ["https://..."]}'
)

_MEDIA_RESEARCH = (
    "Proofhouse generates images, video, speech and music through many API services. Someone asked for media service "
    "{service_id}, which Proofhouse does not know yet. Research its HTTP API: base URL, auth, request path and JSON "
    "body with {{prompt}} and {{model}}, and where the finished file is in the answer. Reply with JSON only: "
    '{"what_it_is": "<one or two sentences>", "name": "<display name>", "kinds": ["image"], "base_url": "https://...", '
    '"key_env": "<ENV or omit>", "auth": "bearer", "unit": "image", "submit": {"path": "/...", "body": {}}, '
    '"result": {"asset": ["path.in.answer"]}, "sources": ["https://..."]}'
)

_TRAIN_RESEARCH = (
    "Proofhouse trains models through online APIs or local commands. Someone asked for training service {service_id}, "
    "which Proofhouse does not know yet. Research either a local command template with {{model}}, {{train}}, "
    "{{epochs}}, {{out}} or the upload/create/status HTTP templates. Reply with JSON only: "
    '{"what_it_is": "<one or two sentences>", "name": "<display name>", "command": ["..."], "sources": ["https://..."]}'
)


# --- parsers ------------------------------------------------------------------------------------


def _host_path_ok(template: str, project: bool) -> bool:
    import os
    from . import hosts

    if project:
        root = Path.cwd().resolve()
        text = template.replace("{project}", str(root))
    else:
        root = Path.home().resolve()
        text = str(root) + template[1:] if template.startswith("~") else template
    path = Path(text.replace("{name}", "sample-name"))
    if not path.is_absolute():
        path = root / path
    path = Path(os.path.normpath(path))
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return hosts.check_name("sample-name") == "sample-name"


def _host_paths_ok(host: dict[str, Any]) -> bool:
    from . import hosts

    for kind in hosts.KINDS:
        spec = host.get(kind)
        if spec is None:
            continue
        if not isinstance(spec, dict) or spec.get("format") not in hosts.FORMATS:
            return False
        for key in ("user", "project"):
            template = spec.get(key)
            if template is None:
                continue
            if not isinstance(template, str) or not _host_path_ok(template, key == "project"):
                return False
    folder = host.get("skills_folder")
    if folder is not None and (not isinstance(folder, str) or folder.startswith(("/", "\\")) or ".." in Path(folder).parts):
        return False
    return True


def parse_platform(platform_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import app_platforms

    data = _json_blob(answer)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    entry = {k: data[k] for k in ("name", "shell", "write", "checks", "build", "host_os") if k in data}
    entry["id"] = platform_id
    entry.update(_meta(data, learned_by=learned_by))
    try:
        app_platforms._validate_entry(entry, "learned")
    except ValueError as exc:
        raise LearnError(str(exc)) from None
    if data.get("web_dir"):
        entry["web_dir"] = data["web_dir"]
    if data.get("refuse_files"):
        entry["refuse_files"] = data["refuse_files"]
    if data.get("refuse_keys"):
        entry["refuse_keys"] = data["refuse_keys"]
    return entry


def parse_host(host_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    data = _json_blob(answer)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    entry: dict[str, Any] = {"id": host_id, "name": str(data.get("name", host_id))}
    for key in ("rule", "agent", "mcp", "note", "skills_folder", "start_hint"):
        if key in data:
            entry[key] = data[key]
    entry.update(_meta(data, learned_by=learned_by))
    if not _host_paths_ok(entry):
        raise LearnError("the model named paths that are not allowed")
    return entry


def parse_deploy(target_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import deploy

    data = _json_blob(answer)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    entry = {k: data[k] for k in ("name", "tool", "install", "command", "key_env") if k in data}
    entry["id"] = target_id
    entry.update(_meta(data, learned_by=learned_by))
    deploy._check(entry, "learned")
    if entry.get("key_env"):
        entry["approved"] = False
    base = entry.get("base_url")
    if isinstance(base, str) and not _https_url(base):
        raise LearnError("a deploy address must be https")
    return entry


def parse_media(service_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import media

    data = _json_blob(answer)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    entry = {k: data[k] for k in ("name", "kinds", "base_url", "key_env", "auth", "unit", "submit", "poll", "result") if k in data}
    entry["id"] = service_id
    entry.update(_meta(data, learned_by=learned_by))
    if not _https_url(str(entry.get("base_url", ""))):
        raise LearnError("a media service address must be https")
    media._parse(entry, "learned")
    if entry.get("key_env"):
        entry["approved"] = False
    return entry


def parse_train(service_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import train

    data = _json_blob(answer)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    entry = {k: data[k] for k in ("name", "command", "upload", "create", "status", "base_url", "key_env", "auth", "provider", "use_hint") if k in data}
    entry["id"] = service_id
    entry.update(_meta(data, learned_by=learned_by))
    if entry.get("base_url") and not _https_url(str(entry["base_url"])):
        raise LearnError("a training service address must be https")
    train._parse(entry, "learned")
    if entry.get("key_env"):
        entry["approved"] = False
    return entry


def _learn(section: str, entry_id: str, id_key: str, prompt: str, parse: Callable[..., dict[str, Any]], ask: Callable[[str], str | None],
           *, learned_by: str) -> dict[str, Any]:
    entry = parse(entry_id, ask(prompt), learned_by=learned_by)
    _save_section(section, entry, id_key)
    return entry


def learn_with_model(section: str, entry_id: str, id_key: str, prompt: str, parse: Callable[..., dict[str, Any]], research: Research) -> dict[str, Any]:
    from . import live

    def ask(prompt_text: str) -> str | None:
        reply = live.run_prompt(
            research.provider_id, research.model, prompt=prompt_text, input_text=None,
            max_output_tokens=4096, max_cost_usd=research.max_cost_usd, transport=research.transport,
        )
        if reply.status != "success":
            raise LearnError(reply.message or reply.code or "the research call did not succeed")
        return reply.output_text

    return _learn(section, entry_id, id_key, prompt, parse, ask, learned_by=f"{research.provider_id}/{research.model}")


def skill_hosts() -> dict[str, tuple[str, str, str]]:
    from .parts import SKILL_HOSTS

    found = dict(SKILL_HOSTS)
    for name, host in addons.contributions("hosts"):
        folder = host.get("skills_folder")
        if not isinstance(folder, str) or not folder.strip():
            continue
        label = str(host.get("name", host["id"]))
        hint = str(host.get("start_hint") or f"a new {label} session")
        if host["id"] not in found or name == LEARNED_PACK:
            found[host["id"]] = (folder.lstrip("./"), label, hint)
    return found


def merge_learned(built_in: dict[str, Any], section: str, *, id_key: str = "id", user: dict[str, Any] | None = None) -> dict[str, Any]:
    found = dict(built_in)
    reserved = set(built_in) | set(user or {})
    for name, raw in addons.contributions(section):
        eid = raw.get(id_key)
        if not isinstance(eid, str):
            continue
        if name == LEARNED_PACK and eid in reserved:
            continue
        found[eid] = raw
    return found


def ensure_platform(platform_id: str, research: Research | None, ask: Callable[[str], str | None] | None = None) -> None:
    from . import app_platforms

    named = plain_platform_id(platform_id)
    if named is None:
        raise LearnError(f"{platform_id!r} is not a plain platform name")
    if named in app_platforms.all_platforms():
        return
    if research is None and ask is None:
        raise _need_model(f"platform {named}")
    prompt = _PLATFORM_RESEARCH.replace("{platform_id}", named)
    if ask is not None:
        _learn("app_platforms", named, "id", prompt, parse_platform, ask, learned_by="unknown")
    else:
        learn_with_model("app_platforms", named, "id", prompt, parse_platform, research)  # type: ignore[arg-type]


def ensure_host(host_id: str, research: Research | None, ask: Callable[[str], str | None] | None = None) -> None:
    from . import hosts

    named = plain_host_id(host_id)
    if named is None:
        raise LearnError(f"{host_id!r} is not a plain host name")
    if named in hosts.all_hosts() or named in skill_hosts():
        return
    if research is None and ask is None:
        raise _need_model(f"host {named}")
    prompt = _HOST_RESEARCH.replace("{host_id}", named)
    if ask is not None:
        _learn("hosts", named, "id", prompt, parse_host, ask, learned_by="unknown")
    else:
        learn_with_model("hosts", named, "id", prompt, parse_host, research)  # type: ignore[arg-type]


def ensure_deploy(target_id: str, research: Research | None, ask: Callable[[str], str | None] | None = None) -> None:
    from . import deploy

    named = plain_service_id(target_id)
    if named is None:
        raise LearnError(f"{target_id!r} is not a plain deploy target name")
    if named in deploy.all_targets():
        return
    if research is None and ask is None:
        raise _need_model(f"deploy target {named}")
    prompt = _DEPLOY_RESEARCH.replace("{target_id}", named)
    if ask is not None:
        _learn("deploy_targets", named, "id", prompt, parse_deploy, ask, learned_by="unknown")
    else:
        learn_with_model("deploy_targets", named, "id", prompt, parse_deploy, research)  # type: ignore[arg-type]


def ensure_media(service_id: str, research: Research | None, ask: Callable[[str], str | None] | None = None) -> None:
    from . import media

    named = plain_service_id(service_id)
    if named is None:
        raise LearnError(f"{service_id!r} is not a plain media service name")
    if media.find(named) is not None:
        return
    if research is None and ask is None:
        raise _need_model(f"media service {named}")
    prompt = _MEDIA_RESEARCH.replace("{service_id}", named)
    if ask is not None:
        _learn("media_providers", named, "id", prompt, parse_media, ask, learned_by="unknown")
    else:
        learn_with_model("media_providers", named, "id", prompt, parse_media, research)  # type: ignore[arg-type]


def ensure_train(service_id: str, research: Research | None, ask: Callable[[str], str | None] | None = None) -> None:
    from . import train

    named = plain_service_id(service_id)
    if named is None:
        raise LearnError(f"{service_id!r} is not a plain training service name")
    if train.find(named) is not None:
        return
    if research is None and ask is None:
        raise _need_model(f"training service {named}")
    prompt = _TRAIN_RESEARCH.replace("{service_id}", named)
    if ask is not None:
        _learn("training_services", named, "id", prompt, parse_train, ask, learned_by="unknown")
    else:
        learn_with_model("training_services", named, "id", prompt, parse_train, research)  # type: ignore[arg-type]


def learned_origin(section: str, entry_id: str, id_key: str = "id") -> bool:
    raw = learned_raw(section, entry_id, id_key)
    return raw is not None


def learned_requires_commands(section: str, entry_id: str, id_key: str = "id") -> bool:
    raw = learned_raw(section, entry_id, id_key)
    if raw is None:
        return False
    if section == "app_platforms":
        return bool((raw.get("build") or {}).get("command"))
    if section == "deploy_targets":
        return bool(raw.get("command"))
    if section == "training_services":
        return bool(raw.get("command"))
    return False
