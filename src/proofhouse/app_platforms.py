"""Data-defined app targets and their offline checks."""

from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from . import make_checks, providers

SCHEMA = "proofhouse.app-platforms/v1"
SHIPPED = Path(__file__).resolve().parent / "data" / "app_platforms.json"
_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
_FILE = re.compile(r"[A-Za-z0-9._/-]+")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_()]*")
_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH", re.IGNORECASE)
# The build's home and temp folders point inside its folder and PATH is the machine's own; platform data may not change them.
_CONTAINED = {"HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "TEMP", "TMP", "TMPDIR", "PATH"}


def _safe_file(name: str) -> bool:
    return bool(_FILE.fullmatch(name)) and not name.startswith(("/", ".")) and ".." not in Path(name).parts \
        and not re.match(r"^[A-Za-z]:", name)


def _words(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(word, str) for word in value)


def _check_build(build: Any) -> bool:
    if not isinstance(build, dict) or not isinstance(build.get("tool"), str) or not isinstance(build.get("install"), str) \
            or not _words(build.get("command")) or not isinstance(build.get("output"), str):
        return False
    if build["output"] and not _safe_file(build["output"]):
        return False
    before, env, home_env = build.get("before", []), build.get("env", []), build.get("home_env", {})
    set_env = build.get("set_env", {})
    if not isinstance(before, list) or not all(_words(step) and step and step[0] for step in [*before, *([build["command"]] if build["command"] else [])]):
        return False
    names = [*env, *home_env, *set_env] if isinstance(env, list) and isinstance(home_env, dict) and isinstance(set_env, dict) else None
    if names is None or not all(isinstance(name, str) and _ENV_NAME.fullmatch(name) and not _SECRET_NAME.search(name)
                                and name.upper() not in _CONTAINED for name in names):
        return False
    if not all(isinstance(value, str) for value in set_env.values()):
        return False
    # Tool homes are usually dot folders (.cargo, .gradle), so a leading dot is allowed here, but not the home itself.
    if not all(isinstance(path, str) and path.lstrip(".") and _safe_file(path.lstrip(".")) and ".." not in Path(path).parts
               for path in home_env.values()):
        return False
    return isinstance(build.get("to_check", ""), str)


def _read(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path} is unreadable: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("platforms"), list):
        raise ValueError(f"{path} must be a {SCHEMA} file with a platforms list")
    for entry in data["platforms"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not _ID.fullmatch(entry["id"]):
            raise ValueError(f"{path}: invalid platform id")
        if not all(isinstance(entry.get(key), str) for key in ("name", "shell", "write")):
            raise ValueError(f"{path}: {entry['id']} needs name, shell and write")
        web_dir = entry.get("web_dir", "")
        if not isinstance(web_dir, str) or (web_dir and not _safe_file(web_dir)):
            raise ValueError(f"{path}: {entry['id']} has an invalid web_dir")
        checks, build, hosts = entry.get("checks"), entry.get("build"), entry.get("host_os")
        if not isinstance(checks, dict) or not isinstance(checks.get("files"), list) or not isinstance(checks.get("json"), dict):
            raise ValueError(f"{path}: {entry['id']} needs file and JSON checks")
        if not all(isinstance(file, str) and _safe_file(file) for file in checks["files"]):
            raise ValueError(f"{path}: {entry['id']} has invalid required files")
        if not all(isinstance(name, str) and _safe_file(name) and isinstance(keys, list)
                   and all(isinstance(key, str) and key for key in keys) for name, keys in checks["json"].items()):
            raise ValueError(f"{path}: {entry['id']} has invalid JSON checks")
        install = checks.get("web_install")
        if install is not None and not (isinstance(install, dict) and all(
                isinstance(install.get(key), str) and _safe_file(install[key]) for key in ("manifest", "service_worker"))):
            raise ValueError(f"{path}: {entry['id']} web_install needs manifest and service_worker file names")
        if not isinstance(checks.get("site", False), bool):
            raise ValueError(f"{path}: {entry['id']} site must be true or false")
        if not _check_build(build):
            raise ValueError(f"{path}: {entry['id']} has invalid build data")
        if not isinstance(hosts, list) or not all(host in ("windows", "macos", "linux") for host in hosts):
            raise ValueError(f"{path}: {entry['id']} has invalid host_os")
    return data["platforms"]


def all_platforms() -> dict[str, dict[str, Any]]:
    found = {entry["id"]: entry for entry in _read(SHIPPED)}
    found.update({entry["id"]: entry for entry in _read(providers.proofhouse_home() / "app_platforms.json")})
    return found


def host_os() -> str:
    return "windows" if os.name == "nt" else "macos" if sys.platform == "darwin" else "linux"


def web_dir(entry: dict[str, Any]) -> str:
    """Where the shared web app goes inside this platform's folder ("" is the folder itself)."""
    return str(entry.get("web_dir", ""))


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.manifests: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and "manifest" in (values.get("rel") or "").split():
            self.manifests.append(values.get("href") or "")
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"] or "")


def static_checks(folder: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    specification = entry["checks"]
    for name in specification["files"]:
        path = folder / name
        checks.append({"check": f"{entry['id']} file {name}", "ok": path.is_file(), "detail": str(path)})
    for name, keys in specification["json"].items():
        try:
            data = json.loads((folder / name).read_text(encoding="utf-8"))
            missing = [key for key in keys if not isinstance(data, dict) or key not in data or not data[key]]
            detail, ok = ("required keys: " + ", ".join(missing), False) if missing else ("valid JSON and required keys", True)
        except (OSError, ValueError) as exc:
            detail, ok = str(exc), False
        checks.append({"check": f"{entry['id']} JSON {name}", "ok": ok, "detail": detail})
    if specification.get("web_install"):
        checks.extend(_install_checks(folder / web_dir(entry), entry))
    return checks


def _inside(folder: Path, ref: str) -> Path | None:
    """A page reference as a file in the folder, checked as text first so nothing outside (such as a network share) is opened."""
    name = ref.split("#")[0].split("?")[0]
    while name.startswith("./"):
        name = name[2:]
    name = name.lstrip("/")
    return folder / name if make_checks.safe_name(name) else None


def _install_checks(folder: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """An installable web app: manifest linked from the page, an icon that exists, a service worker that is registered."""
    manifest_name = entry["checks"]["web_install"]["manifest"]
    worker_name = entry["checks"]["web_install"]["service_worker"]
    label = entry["id"]
    page = (folder / "index.html").read_text(encoding="utf-8") if (folder / "index.html").is_file() else ""
    links = _Links()
    links.feed(page)
    manifest_linked = any(_inside(folder, href) == folder / manifest_name for href in links.manifests)
    scripts = "\n".join(path.read_text(encoding="utf-8") for src in links.scripts
                        if (path := _inside(folder, src)) is not None and path.is_file())
    registered = bool(re.search(r"serviceWorker\s*\.\s*register\s*\(\s*['\"](?:\./|/)?" + re.escape(worker_name) + r"['\"]", page + scripts))
    try:
        manifest = json.loads((folder / manifest_name).read_text(encoding="utf-8"))
        icons = manifest.get("icons") if isinstance(manifest, dict) else None
        icon_ok = isinstance(icons, list) and bool(icons) and any(
            isinstance(icon, dict) and isinstance(icon.get("src"), str)
            and (path := _inside(folder, icon["src"])) is not None and path.is_file() for icon in icons)
    except (OSError, ValueError):
        icon_ok = False
    return [
        {"check": f"{label} manifest linked", "ok": manifest_linked, "detail": manifest_name},
        {"check": f"{label} manifest icon", "ok": icon_ok, "detail": "at least one icon with src"},
        {"check": f"{label} service worker exists", "ok": (folder / worker_name).is_file(), "detail": worker_name},
        {"check": f"{label} service worker registered", "ok": registered, "detail": worker_name},
    ]


def _fill(words: list[str], folder: Path, name: str) -> list[str]:
    return [word.replace("{folder}", str(folder)).replace("{name}", name) for word in words]


def _build_env(build: dict[str, Any]) -> dict[str, str]:
    """Tool locations the build needs from the real machine; never secrets (names like *KEY* or *TOKEN* are refused)."""
    env = {name: os.environ[name] for name in build.get("env", []) if name in os.environ}
    for name, relative in build.get("home_env", {}).items():
        env[name] = os.environ.get(name) or str(Path.home() / relative)
    env.update(build.get("set_env", {}))
    return env


def build_check(folder: Path, entry: dict[str, Any], allow_commands: bool, name: str) -> dict[str, Any]:
    build = entry["build"]
    check = f"{entry['id']} build"
    note = {"to_check": build["to_check"]} if build.get("to_check") else {}
    if not build["command"]:
        return {"check": check, "ok": None, "detail": "no outside build tool required"}
    if not allow_commands:
        return {"check": check, "ok": None, "detail": make_checks.NOT_ALLOWED, **note}
    if host_os() not in entry["host_os"]:
        return {"check": check, "ok": None, "detail": "not built: needs " + ", ".join(entry["host_os"]), **note}
    steps = [_fill(step, folder, name) for step in [*build.get("before", []), build["command"]]]
    env, timeout = _build_env(build), int(build.get("timeout", 600))
    for argv in steps:
        # Found just before it runs, so a setup step can make a tool that a later step uses.
        executable = make_checks._command(argv[0], [], folder)
        if executable is None:
            return {"check": check, "ok": None, "detail": f"not built: {argv[0]} not found (install: {build['install']})", **note}
        # Windows runs .cmd/.bat files (npm, npx) through cmd.exe, which would read these characters as commands.
        if executable[0].lower().endswith((".cmd", ".bat")) and any(set(word) & set('&|^<>%!"') for word in argv):
            return {"check": check, "ok": False, "detail": f"not built: `{' '.join(argv)}` has characters cmd.exe would run", **note}
        outcome = make_checks.build([*executable, *argv[1:]], folder, timeout, env)
        if not outcome["ok"]:
            step = "build" if argv is steps[-1] else "setup step"
            return {"check": check, **outcome, "detail": f"{step} `{' '.join(argv)}` failed: {outcome['detail']}",
                    "command": argv, **note}
    output = build["output"]
    if output and not (folder / output).exists():
        return {"check": check, "ok": False, "detail": f"build finished but {output} is missing", "command": steps[-1], **note}
    return {"check": check, **outcome, "command": steps[-1], **note}
