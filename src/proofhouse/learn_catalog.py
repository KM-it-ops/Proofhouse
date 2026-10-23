"""Research and learn entries Proofhouse does not know yet (platforms, hosts, deploy targets, media and training services).

Each list uses the same steps as make kinds (``learn.py``): pull the JSON out of the answer, record where it
came from, one research call through the spend gate, check it, and save it in the ``learned`` add-on pack.
Built-in entries come first, then yours, then other add-on packs, and learned entries last: a learned entry
never replaces one that is already there. Every learned entry is saved unapproved. Until you approve that
one entry, using it stops before anything runs, is sent or is written.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Callable
from urllib.parse import urlparse

from . import addons, learn, providers
from .learn import LEARNED_PACK, SOURCES_NOTE, LearnError, pack_path

_LISTS = ("app_platforms", "hosts", "deploy_targets", "media_providers", "training_services")
_NAME_LIMIT = 100
_TEXT_LIMIT = 2000
_LIST_LIMIT = 50
_URLISH = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")

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
    return learn.extract_answer(answer)


def _meta(answer: dict[str, Any], *, learned_by: str) -> dict[str, Any]:
    return learn.provenance(answer, learned_by=learned_by, what_limit=_TEXT_LIMIT, source_limit=_LIST_LIMIT)


def _pack_raw() -> dict[str, Any]:
    return learn.read_pack()


def _save_section(section: str, entry: dict[str, Any], id_key: str) -> Path:
    return learn.save_section(section, entry, id_key)


def learned_raw(section: str, entry_id: str, id_key: str = "id") -> dict[str, Any] | None:
    raw = learn.read_pack()
    for entry in raw.get(section, []):
        if isinstance(entry, dict) and entry.get(id_key) == entry_id:
            return entry
    return None


def approve(entry_id: str, *, list_name: str | None = None) -> Path:
    """Approve one learned entry. The same id in two lists is left alone until ``--list`` names one."""
    raw = learn.read_pack()
    found: list[str] = []
    for section in _LISTS:
        items = raw.get(section, [])
        if isinstance(items, list) and any(isinstance(entry, dict) and entry.get("id") == entry_id for entry in items):
            found.append(section)
    if not found:
        raise LearnError(f"no learned entry named {entry_id!r}; see `proofhouse addons list`")
    if list_name is None and len(found) > 1:
        raise LearnError(f"{entry_id!r} is in more than one list ({', '.join(found)}); nothing was changed. Name one with --list")
    if list_name is not None and list_name not in found:
        raise LearnError(f"no learned {entry_id!r} in {list_name}; it is in {', '.join(found)}")
    chosen = {list_name} if list_name else set(found)
    for section in chosen:
        items = raw[section]
        for index, entry in enumerate(items):
            if isinstance(entry, dict) and entry.get("id") == entry_id:
                items[index] = {**entry, "approved": True}
    return learn.write_pack(raw)


def needs_approval(entry: dict[str, Any]) -> bool:
    return entry.get("approved") is not True


def origin_of(active: Any) -> str | None:
    if isinstance(active, dict):
        value = active.get("origin")
        return value if isinstance(value, str) else None
    value = getattr(active, "origin", None)
    return value if isinstance(value, str) else None


def is_learned(active: Any) -> bool:
    return origin_of(active) == f"add-on {LEARNED_PACK}"


def unapproved(section: str, entry_id: str, active: Any) -> dict[str, Any] | None:
    """The learned entry when it is the one in use and has not been approved. A built-in or your own entry hides it."""
    if not is_learned(active):
        return None
    learned = learned_raw(section, entry_id)
    if learned is None or learned.get("approved") is True:
        return None
    return learned


def would_do(entry: dict[str, Any]) -> str:
    """What a learned entry would do, with nothing run: address, command, env, paths, key name and sources."""
    parts: list[str] = []
    build = entry.get("build") if isinstance(entry.get("build"), dict) else {}
    submit = entry.get("submit") if isinstance(entry.get("submit"), dict) else {}
    if isinstance(entry.get("base_url"), str):
        path = submit.get("path") if isinstance(submit.get("path"), str) else ""
        parts.append(f"address: {entry['base_url']}{path}")
        for label in ("upload", "create", "status"):
            spec = entry.get(label)
            if isinstance(spec, dict) and isinstance(spec.get("path"), str):
                parts.append(f"{label}: {entry['base_url'].rstrip('/')}{spec['path']}")
    result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
    if isinstance(result.get("ext"), str) and result["ext"]:
        parts.append(f"file type: {result['ext']}")
    if build.get("before"):
        parts.append(f"before: {build['before']}")
    command = build.get("command") or entry.get("command")
    if command:
        parts.append(f"command: {command}")
    if build.get("env"):
        parts.append(f"env: {build['env']}")
    if build.get("set_env"):
        parts.append(f"set_env: {build['set_env']}")
    paths: list[str] = []
    checks = entry.get("checks") if isinstance(entry.get("checks"), dict) else {}
    paths.extend(path for path in checks.get("files", []) if isinstance(path, str))
    paths.extend(path for path in checks.get("json", {}) if isinstance(path, str))
    web_install = checks.get("web_install") if isinstance(checks.get("web_install"), dict) else {}
    paths.extend(path for path in web_install.values() if isinstance(path, str))
    paths.extend(path for path in entry.get("refuse_files", []) if isinstance(path, str))
    paths.extend(path for path in entry.get("refuse_keys", {}) if isinstance(path, str))
    if isinstance(build.get("output"), str) and build["output"]:
        paths.append(build["output"])
    if isinstance(entry.get("web_dir"), str) and entry["web_dir"]:
        paths.append(entry["web_dir"])
    home_env = build.get("home_env") if isinstance(build.get("home_env"), dict) else {}
    paths.extend(path for path in home_env.values() if isinstance(path, str))
    for kind in ("rule", "agent", "mcp"):
        spec = entry.get(kind)
        if isinstance(spec, dict):
            paths.extend(spec[key] for key in ("user", "project") if isinstance(spec.get(key), str))
    if isinstance(entry.get("skills_folder"), str):
        paths.append(entry["skills_folder"])
    if paths:
        parts.append("paths: " + ", ".join(paths))
    if entry.get("key_env"):
        parts.append(f"key: {entry['key_env']}")
    who = str(entry.get("learned_by") or "the model")
    for field in ("install", "use_hint"):
        text = entry.get(field)
        if isinstance(text, str) and text:
            parts.append(f"{field}: {text} (suggested by {who}, not checked)")
    sources = ", ".join(entry.get("sources") or []) or "none"
    parts.append(f"Sources ({entry.get('sources_note', SOURCES_NOTE)}): {sources}")
    return "; ".join(parts)


def refusal_message(entry: dict[str, Any], *, thing: str, command: str) -> str:
    return (f"{thing} is not approved yet; nothing was run, sent or written. {would_do(entry)}. "
            f"After you check them, run: {command}")


def suggested(text: str, learned_by: str | None) -> str:
    return f"{text} (suggested by {learned_by or 'the model'}, not checked)"


def command_env(folder: Path, key_env: str | None = None) -> dict[str, str]:
    """The cleaned command environment, plus only the key variable this entry names."""
    from .make_checks import _environment

    env = _environment(folder)
    if isinstance(key_env, str) and key_env and key_env in os.environ:
        env[key_env] = os.environ[key_env]
    return env


APPROVE_CMD = "proofhouse addons approve learned"


def plain_platform_id(text: str) -> str | None:
    name = text.strip().lower()
    return name if _PLATFORM_ID.fullmatch(name) else None


def plain_host_id(text: str) -> str | None:
    """A host id exactly as typed, in lowercase. Anything else is refused, never rewritten."""
    name = text.strip().lower()
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


def leaves_root(path: Path, root: Path) -> bool:
    """True when ``path``, or where it points after links are followed, is outside ``root``."""
    folded = Path(os.path.normpath(path))
    root_folded = Path(os.path.normpath(root))
    try:
        folded.relative_to(root_folded)
    except ValueError:
        return True
    try:
        folded.resolve().relative_to(root_folded.resolve())
    except ValueError:
        return True
    return False


def in_blocked_area(path: Path) -> bool:
    """True when ``path`` is inside ``~/.ssh`` or Proofhouse's own folder."""
    home = Path.home().resolve()
    areas = [home / ".ssh", providers.proofhouse_home()]
    folded = Path(os.path.normpath(path))
    resolved = folded.resolve()
    for area in areas:
        area_folded = Path(os.path.normpath(area))
        bases = [area_folded]
        if area_folded.exists():
            bases.append(area_folded.resolve())
        for candidate in (folded, resolved):
            for base in bases:
                try:
                    candidate.relative_to(base)
                except ValueError:
                    continue
                return True
    return False


def path_rejected(path: Path, root: Path) -> str | None:
    if leaves_root(path, root) or in_blocked_area(path):
        return f"{path} is outside the home folder"
    return None


def _placed(folder: str) -> Path:
    """Where a skills folder lands. An absolute path, or one with a drive letter on any system, is not
    joined onto the home folder."""
    home = Path.home().resolve()
    raw = Path(folder)
    if raw.is_absolute() or PureWindowsPath(folder).drive or folder.startswith(("\\\\", "//", "/", "\\")):
        return Path(os.path.normpath(folder))
    return Path(os.path.normpath(home / folder))


def _host_path_ok(template: str, project: bool) -> bool:
    from . import hosts

    if any(part in (".", "..") for part in re.split(r"[\\/]", template)):
        return False
    if project:
        root = Path.cwd().resolve()
        text = template.replace("{project}", str(root))
    else:
        root = Path.home().resolve()
        text = str(root) + template[1:] if template.startswith("~") else template
    path = Path(text.replace("{name}", "sample-name"))
    if not path.is_absolute() and not PureWindowsPath(text).drive:
        path = root / path
    path = Path(os.path.normpath(path))
    if path_rejected(path, root if project else Path.home().resolve()):
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
    if folder is not None:
        if not isinstance(folder, str) or any(part in (".", "..") for part in re.split(r"[\\/]", folder)) \
                or path_rejected(_placed(folder), Path.home().resolve()) \
                or path_rejected(_placed(folder) / "skills", Path.home().resolve()):
            return False
    return True


def _within_limits(data: dict[str, Any]) -> None:
    def walk(value: Any, key: str | None = None) -> None:
        if isinstance(value, str):
            limit = _NAME_LIMIT if key == "name" else _TEXT_LIMIT
            if len(value) > limit:
                raise LearnError("the model's answer is over the size limit; nothing was saved")
        elif isinstance(value, list):
            if len(value) > _LIST_LIMIT:
                raise LearnError("the model's answer is over the size limit; nothing was saved")
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for name, item in value.items():
                if not isinstance(name, str) or len(name) > _TEXT_LIMIT:
                    raise LearnError("the model's answer is over the size limit; nothing was saved")
                walk(item, name)

    walk(data)


def _builtin_entries(section: str) -> list[dict[str, Any]]:
    from . import app_platforms, deploy, hosts, media, train

    paths = {
        "app_platforms": (app_platforms.SHIPPED, "platforms"),
        "hosts": (hosts.SHIPPED_PATH, "hosts"),
        "deploy_targets": (deploy.SHIPPED_PATH, "targets"),
        "media_providers": (media.SHIPPED_PATH, "providers"),
        "training_services": (train.SHIPPED_PATH, "services"),
    }
    path, key = paths[section]
    data = json.loads(path.read_text(encoding="utf-8"))
    return [entry for entry in data.get(key, []) if isinstance(entry, dict)]


def _allowed_keys(section: str, field: str) -> set[str]:
    found: set[str] = set()
    for entry in _builtin_entries(section):
        value = entry.get(field)
        if isinstance(value, dict):
            found.update(value)
    return found


def _builtin_env_names() -> set[str]:
    names: set[str] = set()
    for entry in _builtin_entries("app_platforms"):
        build = entry.get("build") if isinstance(entry.get("build"), dict) else {}
        if isinstance(build.get("env"), list):
            names.update(name for name in build["env"] if isinstance(name, str))
        for key in ("set_env", "home_env"):
            if isinstance(build.get(key), dict):
                names.update(build[key])
    return names


def _max_timeout() -> int:
    found = [600]
    for entry in _builtin_entries("app_platforms"):
        build = entry.get("build") if isinstance(entry.get("build"), dict) else {}
        if type(build.get("timeout")) is int:
            found.append(build["timeout"])
    return max(found)


def _filter_build(build: dict[str, Any]) -> dict[str, Any]:
    allowed = _allowed_keys("app_platforms", "build")
    kept = {key: value for key, value in build.items() if key in allowed} if allowed else dict(build)
    names = _builtin_env_names()
    if isinstance(kept.get("env"), list):
        kept["env"] = [name for name in kept["env"] if isinstance(name, str) and name in names]
    for key in ("set_env", "home_env"):
        if isinstance(kept.get(key), dict):
            kept[key] = {name: value for name, value in kept[key].items() if name in names}
    if "timeout" in kept:
        timeout = kept["timeout"]
        if type(timeout) is not int or not 1 <= timeout <= _max_timeout():
            raise LearnError("build timeout must be a whole number of seconds, at most the largest built-in timeout")
    return kept


def _only_known(section: str, field: str, value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    if field == "build":
        return _filter_build(value)
    allowed = _allowed_keys(section, field)
    kept = {key: item for key, item in value.items() if key in allowed} if allowed else dict(value)
    if field == "checks" and isinstance(kept.get("web_install"), dict):
        inner: set[str] = set()
        for entry in _builtin_entries(section):
            checks = entry.get("checks")
            if isinstance(checks, dict) and isinstance(checks.get("web_install"), dict):
                inner.update(checks["web_install"])
        if inner:
            kept["web_install"] = {key: item for key, item in kept["web_install"].items() if key in inner}
    return kept


def _answer(answer: str | None, *, thing: str) -> dict[str, Any]:
    data = learn.extract_answer(answer, thing=thing)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    _within_limits(data)
    return data


_PROGRAM_EXT = frozenset(
    "exe com bat cmd ps1 psm1 vbs vbe js jse wsf wsh msi msp scr lnk pif cpl hta reg jar sh py pyw".split()
)
_FILE_EXT = re.compile(r"[A-Za-z0-9]{1,10}")


def answer_depth_limit() -> int:
    """How deep a built-in entry of any learned list is. A research answer deeper than this is refused."""
    deepest = 1
    for section in _LISTS:
        for entry in _builtin_entries(section):
            deepest = max(deepest, learn.nesting(entry))
    return deepest


def service_path_ok(base_url: str, path: str) -> bool:
    """True when ``path`` joined to ``base_url`` is https on exactly that host.

    The join is the one the request uses: the base with one trailing slash removed, then the path.
    Anything else is refused, never rewritten.
    """
    if not isinstance(base_url, str) or not isinstance(path, str):
        return False
    if not path.startswith("/") or path.startswith("//") or any(char.isspace() for char in path):
        return False
    url = base_url.rstrip("/") + path
    parsed, base = urlparse(url), urlparse(base_url)
    host = (parsed.hostname or "").lower()
    base_host = (base.hostname or "").lower()
    if parsed.scheme != "https" or not host or host != base_host:
        return False
    if parsed.username or parsed.password or (parsed.path or "").startswith("//"):
        return False
    return public_https(url)


def _train_paths_ok(entry: dict[str, Any]) -> bool:
    """Every path on a learned training service, joined to its base, stays on that host."""
    base = entry.get("base_url")
    if not base:
        return True
    if not isinstance(base, str):
        return False

    def bad(spec: Any) -> bool:
        if isinstance(spec, dict):
            for key, value in spec.items():
                if key == "path":
                    if not service_path_ok(base, value if isinstance(value, str) else ""):
                        return True
                elif bad(value):
                    return True
        elif isinstance(spec, list):
            return any(bad(item) for item in spec)
        return False

    return not any(bad(entry.get(name)) for name in ("upload", "create", "status"))


def media_ext_problem(ext: object) -> str | None:
    """Why ``ext`` cannot be the suffix of a learned media file, or ``None`` when it can."""
    if isinstance(ext, str) and _FILE_EXT.fullmatch(ext) and ext.lower() not in _PROGRAM_EXT:
        return None
    return "a media file type must be 1 to 10 letters or digits, and not a program"


def public_https(url: str) -> bool:
    """True for https on a public host. Local, private, link-local and reserved addresses are refused."""
    if not isinstance(url, str) or not url.startswith("https://") or any(char.isspace() for char in url):
        return False
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if not host or host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped
    return bool(address.is_global)


def _command_urls_ok(command: Any) -> bool:
    if not isinstance(command, list):
        return True
    for word in command:
        if not isinstance(word, str):
            return False
        for match in _URLISH.finditer(word):
            if not match.group(0).lower().startswith("https://"):
                return False
    return True


def _finish(entry: dict[str, Any], data: dict[str, Any], *, learned_by: str) -> dict[str, Any]:
    entry.update(_meta(data, learned_by=learned_by))
    entry["approved"] = False
    return entry


def parse_platform(platform_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import app_platforms

    data = _answer(answer, thing=f"platform {platform_id}")
    entry = {key: data[key] for key in ("name", "shell", "write", "checks", "build", "host_os") if key in data}
    for field in ("checks", "build"):
        if field in entry:
            entry[field] = _only_known("app_platforms", field, entry[field])
    entry["id"] = platform_id
    _finish(entry, data, learned_by=learned_by)
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
    data = _answer(answer, thing=f"host {host_id}")
    entry: dict[str, Any] = {"id": host_id, "name": str(data.get("name", host_id))}
    for key in ("rule", "agent", "mcp", "note", "skills_folder", "start_hint"):
        if key in data:
            entry[key] = _only_known("hosts", key, data[key]) if key in ("rule", "agent", "mcp") else data[key]
    _finish(entry, data, learned_by=learned_by)
    if not _host_paths_ok(entry):
        raise LearnError("the model named paths that are not allowed")
    return entry


def parse_deploy(target_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import deploy

    data = _answer(answer, thing=f"deploy target {target_id}")
    if "base_url" in data and not public_https(str(data.get("base_url"))):
        raise LearnError("a deploy address must be https")
    if not _command_urls_ok(data.get("command")):
        raise LearnError("a deploy address must be https")
    entry = {key: data[key] for key in ("name", "tool", "install", "command", "key_env") if key in data}
    entry["id"] = target_id
    _finish(entry, data, learned_by=learned_by)
    deploy._check(entry, "learned")
    return entry


def parse_media(service_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import media

    data = _answer(answer, thing=f"media service {service_id}")
    entry = {key: data[key] for key in ("name", "kinds", "base_url", "key_env", "auth", "unit", "submit", "poll", "result") if key in data}
    for field in ("submit", "poll", "result"):
        if field in entry:
            entry[field] = _only_known("media_providers", field, entry[field])
    entry["id"] = service_id
    _finish(entry, data, learned_by=learned_by)
    if not public_https(str(entry.get("base_url", ""))):
        raise LearnError("a media service address must be https")
    result = entry.get("result")
    if isinstance(result, dict) and "ext" in result:
        problem = media_ext_problem(result.get("ext"))
        if problem:
            raise LearnError(problem)
    media._parse(entry, "learned")
    return entry


def parse_train(service_id: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    from . import train

    data = _answer(answer, thing=f"training service {service_id}")
    entry = {key: data[key] for key in ("name", "command", "upload", "create", "status", "base_url", "key_env", "auth", "provider", "use_hint") if key in data}
    for field in ("upload", "create", "status"):
        if field in entry:
            entry[field] = _only_known("training_services", field, entry[field])
    entry["id"] = service_id
    _finish(entry, data, learned_by=learned_by)
    if not _command_urls_ok(entry.get("command")):
        raise LearnError("a training service address must be https")
    if entry.get("base_url") and not public_https(str(entry["base_url"])):
        raise LearnError("a training service address must be https")
    if not _train_paths_ok(entry):
        raise LearnError("a training service address must stay on its own host")
    train._parse(entry, "learned")
    return entry


def _learn(section: str, entry_id: str, id_key: str, prompt: str, parse: Callable[..., dict[str, Any]], ask: Callable[[str], str | None],
           *, learned_by: str) -> dict[str, Any]:
    entry = parse(entry_id, ask(prompt), learned_by=learned_by)
    _save_section(section, entry, id_key)
    return entry


def learn_with_model(section: str, entry_id: str, id_key: str, prompt: str, parse: Callable[..., dict[str, Any]], research: Research) -> dict[str, Any]:
    def ask(prompt_text: str) -> str | None:
        return learn.ask_model(
            research.provider_id, research.model, prompt_text, max_cost_usd=research.max_cost_usd,
            max_output_tokens=4096, transport=research.transport,
        )

    return _learn(section, entry_id, id_key, prompt, parse, ask, learned_by=f"{research.provider_id}/{research.model}")


def split_contributions(section: str) -> tuple[list[tuple[str, dict[str, Any]]], list[tuple[str, dict[str, Any]]]]:
    """Other add-on entries, then learned entries. Learned is always last and never replaces."""
    others: list[tuple[str, dict[str, Any]]] = []
    learned: list[tuple[str, dict[str, Any]]] = []
    for name, raw in addons.contributions(section):
        (learned if name == LEARNED_PACK else others).append((name, raw))
    return others, learned


def _skill_host_table() -> dict[str, tuple[tuple[str, str, str], dict[str, Any] | None]]:
    """id -> (folder row, the entry that supplied it). None marks a built-in skill-host constant."""
    from . import hosts
    from .parts import SKILL_HOSTS

    found: dict[str, tuple[tuple[str, str, str], dict[str, Any] | None]] = {
        host_id: (row, None) for host_id, row in SKILL_HOSTS.items()
    }

    def consider(host: dict[str, Any], *, replace: bool, learned: bool) -> None:
        folder = host.get("skills_folder")
        if not isinstance(folder, str) or not folder.strip() or not isinstance(host.get("id"), str):
            return
        if host["id"] in found and not replace:
            return
        label = str(host.get("name", host["id"]))
        hint = str(host.get("start_hint") or f"a new {label} session")
        entry = {**host, "origin": f"add-on {LEARNED_PACK}"} if learned else host
        found[host["id"]] = ((folder, label, hint), entry)

    for host in hosts._read_hosts(providers.proofhouse_home() / "hosts.json"):
        consider(host, replace=True, learned=False)
    others, learned_rows = split_contributions("hosts")
    for _name, host in others:
        consider(host, replace=True, learned=False)
    for _name, host in learned_rows:
        consider(host, replace=False, learned=True)
    return found


def skill_hosts() -> dict[str, tuple[str, str, str]]:
    """Built-in skill hosts, then yours, then other add-on packs, then learned if the id is still free."""
    return {host_id: row for host_id, (row, _entry) in _skill_host_table().items()}


def active_skill_host(host_id: str) -> dict[str, Any] | None:
    """The entry that supplies this host's skills folder, so approval checks that same entry.

    A built-in skill-host constant has no entry of its own; the catalog host is used instead.
    A learned host that fills a gap (for example ``codex``) is the entry install will write into.
    """
    from . import hosts

    found = _skill_host_table().get(host_id)
    if found is None:
        return hosts.all_hosts().get(host_id)
    entry = found[1]
    return hosts.all_hosts().get(host_id) if entry is None else entry


def merge_learned(built_in: dict[str, Any], section: str, *, id_key: str = "id", user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Built-in, then yours, then other add-on packs. A learned entry is added only when the id is still free."""
    found = dict(built_in)
    for eid, raw in (user or {}).items():
        found[eid] = raw
    others, learned = split_contributions(section)
    for _name, raw in others:
        eid = raw.get(id_key)
        if isinstance(eid, str):
            found[eid] = raw
    for _name, raw in learned:
        eid = raw.get(id_key)
        if isinstance(eid, str) and eid not in found:
            found[eid] = {**raw, "origin": f"add-on {LEARNED_PACK}"}
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
