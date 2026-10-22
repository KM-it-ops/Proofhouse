"""Data-defined app targets and their offline checks.

Optional platform fields (custom platforms may leave them out):
  refuse_files  file names the model may not write, in any letter case; * and ? wildcards work, and a pattern
                without "/" matches the base name in any folder, one with "/" the whole relative path
  refuse_keys   {file pattern: [dotted.key, ...]}: keys that may not appear in a matching model-written JSON file
  build.tool_package, build.tool_bin  the npm package that must provide the build tool and the one bin name it
                provides; the model's package.json must list it, and no other installed top-level package may
                declare that bin. Use `npx --no-install` in the steps so nothing else is downloaded.
Existing fields such as home_env and set_env are described in the code below.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import stat
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from . import make_checks, providers

SCHEMA = "proofhouse.app-platforms/v1"
SHIPPED = Path(__file__).resolve().parent / "data" / "app_platforms.json"
_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
_FILE = re.compile(r"[A-Za-z0-9._/-]+")
_NPM_NAME = re.compile(r"(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*")
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
    output_template = build["output"].replace("{mainBinaryName}", "app").replace("{productName}", "app")
    if build["output"] and not _safe_file(output_template):
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
    package, tool_bin = build.get("tool_package"), build.get("tool_bin")
    if (package is None) != (tool_bin is None) or not all(item is None or isinstance(item, str) and _NPM_NAME.fullmatch(item)
                                                          for item in (package, tool_bin)):
        return False
    return isinstance(build.get("to_check", ""), str)


def _check_refusals(entry: dict[str, Any]) -> bool:
    files, keys = entry.get("refuse_files", []), entry.get("refuse_keys", {})
    return isinstance(files, list) and all(isinstance(name, str) and name for name in files) and isinstance(keys, dict) \
        and all(isinstance(name, str) and _safe_file(name) and isinstance(found, list)
                and all(isinstance(key, str) and key for key in found) for name, found in keys.items())


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
        _validate_entry(entry, str(path))
    return data["platforms"]


def _validate_entry(entry: dict[str, Any], where: str) -> None:
    if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not _ID.fullmatch(entry["id"]):
        raise ValueError(f"{where}: invalid platform id")
    if not all(isinstance(entry.get(key), str) for key in ("name", "shell", "write")):
        raise ValueError(f"{where}: {entry['id']} needs name, shell and write")
    web_dir = entry.get("web_dir", "")
    if not isinstance(web_dir, str) or (web_dir and not _safe_file(web_dir)):
        raise ValueError(f"{where}: {entry['id']} has an invalid web_dir")
    checks, build, hosts = entry.get("checks"), entry.get("build"), entry.get("host_os")
    if not isinstance(checks, dict) or not isinstance(checks.get("files"), list) or not isinstance(checks.get("json"), dict):
        raise ValueError(f"{where}: {entry['id']} needs file and JSON checks")
    if not all(isinstance(file, str) and _safe_file(file) for file in checks["files"]):
        raise ValueError(f"{where}: {entry['id']} has invalid required files")
    if not all(isinstance(name, str) and _safe_file(name) and isinstance(keys, list)
               and all(isinstance(key, str) and key for key in keys) for name, keys in checks["json"].items()):
        raise ValueError(f"{where}: {entry['id']} has invalid JSON checks")
    install = checks.get("web_install")
    if install is not None and not (isinstance(install, dict) and all(
            isinstance(install.get(key), str) and _safe_file(install[key]) for key in ("manifest", "service_worker"))):
        raise ValueError(f"{where}: {entry['id']} web_install needs manifest and service_worker file names")
    if not isinstance(checks.get("site", False), bool):
        raise ValueError(f"{where}: {entry['id']} site must be true or false")
    if not _check_build(build):
        raise ValueError(f"{where}: {entry['id']} has invalid build data")
    if not _check_refusals(entry):
        raise ValueError(f"{where}: {entry['id']} has invalid refuse_files or refuse_keys")
    if not isinstance(hosts, list) or not all(host in ("windows", "macos", "linux") for host in hosts):
        raise ValueError(f"{where}: {entry['id']} has invalid host_os")


def all_platforms() -> dict[str, dict[str, Any]]:
    from . import learn_catalog

    shipped = {entry["id"]: entry for entry in _read(SHIPPED)}
    user = {entry["id"]: entry for entry in _read(providers.proofhouse_home() / "app_platforms.json")}
    found = learn_catalog.merge_learned(shipped, "app_platforms", user=user)
    found.update(user)
    return found


def host_os() -> str:
    return "windows" if os.name == "nt" else "macos" if sys.platform == "darwin" else "linux"


def web_dir(entry: dict[str, Any]) -> str:
    """Where the shared web app goes inside this platform's folder ("" is the folder itself)."""
    return str(entry.get("web_dir", ""))


_DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
_LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "pnpm-workspace.yaml",
              "bun.lock", "bun.lockb", "bunfig.toml"}
_VERSION = re.compile(r"[0-9A-Za-z.^~<>=|*+\- ]*")
_TAG = re.compile(r"[A-Za-z][A-Za-z0-9-]*")


def _registry_spec(spec: str) -> bool:
    """A semver version or range, a plain tag, or nothing; never a path, URL, git source, alias, workspace link or tarball."""
    if _TAG.fullmatch(spec):
        return True
    trimmed = spec.strip()
    return bool(_VERSION.fullmatch(spec)) and not trimmed.lower().endswith((".tar", ".tgz", ".tar.gz")) \
        and (not spec or bool(trimmed.strip(".")))


def _strings(value: object) -> list[str]:
    """Every string inside a JSON value, found without recursion so deep nesting cannot crash it."""
    found: list[str] = []
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            found.append(item)
        elif isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return found


def _load(name: str, text: str) -> object:
    try:
        return json.loads(text)
    except RecursionError as exc:
        raise ValueError(f"{name} is nested too deeply") from exc
    except ValueError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc


def check_packages(files: dict[str, str]) -> None:
    """Refuse a package.json that is not registry-only, and any lockfile, since --ignore-scripts does not stop a
    local or aliased package from linking a fake build tool into node_modules/.bin."""
    for name, text in files.items():
        base = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if base in _LOCKFILES:
            raise ValueError(f"the model may not write {name}: a lockfile or package-manager setting can point packages at local paths (package.json must use the registry)")
        if base != "package.json":
            continue
        data = _load(name, text)
        if not isinstance(data, dict):
            raise ValueError(f"{name} must be a JSON object")
        if "workspaces" in data:
            raise ValueError(f"{name} may not use workspaces (they link local packages)")
        specs: list[str] = []
        for field in _DEPENDENCY_FIELDS:
            deps = data.get(field, {})
            if not isinstance(deps, dict) or not all(isinstance(spec, str) for spec in deps.values()):
                raise ValueError(f"{name}: {field} must be an object of version strings")
            specs.extend(deps.values())
        for field in ("overrides", "resolutions"):
            specs.extend(_strings(data.get(field)))
        pnpm = data.get("pnpm", {})
        if not isinstance(pnpm, dict):
            raise ValueError(f"{name}: pnpm must be an object")
        if "patchedDependencies" in pnpm:
            raise ValueError(f"{name} may not use pnpm patchedDependencies (they apply local patch files)")
        specs.extend(_strings(pnpm.get("overrides")))
        bad = [spec for spec in specs if not _registry_spec(spec)]
        if bad:
            raise ValueError(f"{name} may only use registry versions, not {', '.join(repr(spec) for spec in bad)}")


def _key_present(data: object, dotted: str) -> bool:
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return False
        data = data[part]
    return True


def _named(name: str, pattern: str) -> bool:
    """Whether a model file matches a platform's pattern, ignoring letter case: a pattern without "/" matches the
    base name in any folder, one with "/" the whole relative path. Patterns may use * and ? wildcards."""
    lowered, pattern = name.replace("\\", "/").lower(), pattern.lower()
    return fnmatch.fnmatchcase(lowered if "/" in pattern else lowered.rsplit("/", 1)[-1], pattern)


def check_platform(files: dict[str, str], entry: dict[str, Any]) -> None:
    """Refuse model files this platform's data forbids (refuse_files, refuse_keys) and a package.json that does not list
    the build tool's package (build.tool_package). Names are compared without regard to letter case."""
    for name in files:
        if any(_named(name, pattern) for pattern in entry.get("refuse_files", [])):
            raise ValueError(f"the model may not write {name}: this platform runs it as build settings or code")
    for target, keys in entry.get("refuse_keys", {}).items():
        for name, text in files.items():
            if not _named(name, target):
                continue
            data = _load(name, text)
            for key in keys:
                if _key_present(data, key):
                    raise ValueError(f"{name} may not set {key}: it runs a program the model chose")
    tool = entry["build"].get("tool_package")
    if tool:
        text = next((text for name, text in files.items() if name.lower() == "package.json"), None)
        data = _load("package.json", text) if text is not None else None
        listed = any(isinstance(data, dict) and isinstance(data.get(field), dict) and tool in data[field]
                     for field in ("dependencies", "devDependencies"))
        if not listed:
            raise ValueError(f"package.json must list {tool} in dependencies or devDependencies (it is the build tool)")


def _tool_problem(folder: Path, tool_package: str, tool_bin: str) -> str | None:
    """Why the installed packages cannot be trusted to give `tool_bin`: the real package is missing, or another one also provides it."""
    root = folder / "node_modules"
    manifests = [*sorted(root.glob("*/package.json")), *sorted(root.glob("@*/*/package.json"))]
    installed: set[str] = set()
    for manifest in manifests:
        package = manifest.parent.relative_to(root).as_posix()
        if manifest.parent.parent == root and package.startswith("@"):
            continue
        installed.add(package)
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError):
            continue
        bin_field = data.get("bin") if isinstance(data, dict) else None
        names = [package.rsplit("/", 1)[-1]] if isinstance(bin_field, str) else list(bin_field) if isinstance(bin_field, dict) else []
        # Without a bin field npm links every file in directories.bin, named after the file.
        folders = data.get("directories") if isinstance(data, dict) and bin_field is None else None
        bin_folder = folders.get("bin") if isinstance(folders, dict) else None
        if isinstance(bin_folder, str):
            target = (manifest.parent / bin_folder).resolve()
            if not target.is_relative_to(manifest.parent.resolve()):
                return f"{package} points directories.bin outside its own folder"
            try:
                names += [name for item in target.rglob("*") if item.is_file() for name in (item.name, item.stem)]
            except OSError as exc:
                return f"could not read {package}'s bin folder: {exc}"
        if package != tool_package and tool_bin.lower() in (str(item).lower() for item in names):
            return f"{package} also provides `{tool_bin}`; it must come only from {tool_package}"
    return None if tool_package in installed else f"{tool_package} is not installed"


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
        except (OSError, ValueError, RecursionError) as exc:
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
    return [word.replace("{folder}", str(folder)).replace("{name}", name)
            .replace("{gradlew}", "./android/gradlew.bat" if os.name == "nt" else "./android/gradlew") for word in words]


def _build_env(build: dict[str, Any]) -> dict[str, str]:
    """Tool locations the build needs from the real machine; never secrets (names like *KEY* or *TOKEN* are refused)."""
    env = {name: os.environ[name] for name in build.get("env", []) if name in os.environ}
    for name, relative in build.get("home_env", {}).items():
        env[name] = os.environ.get(name) or str(Path.home() / relative)
    env.update(build.get("set_env", {}))
    return env


# Enough to hash any real app bundle; past it files are compared by size and time only, so a huge file can't stall the check.
_HASH_LIMIT = 1024 ** 3


def _is_link(item: Path) -> bool:
    """A symbolic link, or on Windows any reparse point, such as a directory junction."""
    if item.is_symlink():
        return True
    return bool(getattr(item.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _link_digest(item: Path) -> str:
    try:
        return "link:" + os.readlink(item)
    except OSError:
        return "reparse point"


def _snapshot(path: Path) -> list[tuple[str, int, int, str]]:
    """Record output contents without following links into another folder or opening anything but plain files."""
    budget = _HASH_LIMIT

    def record(item: Path) -> tuple[str, int, int, str]:
        nonlocal budget
        info = item.lstat()
        if _is_link(item):
            digest = _link_digest(item)
        elif not stat.S_ISREG(info.st_mode):
            # A pipe or device would block or never end when opened.
            digest = f"special:{stat.S_IFMT(info.st_mode)}"
        elif info.st_size > budget:
            digest = "unhashed"
        else:
            budget -= info.st_size
            with item.open("rb") as stream:
                hasher = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
                digest = hasher.hexdigest()
        return str(item), info.st_mtime_ns, info.st_size, digest

    if _is_link(path) or not path.is_dir():
        return [record(path)]
    found = []
    for root, directories, files in os.walk(path, followlinks=False):
        for name in directories[:]:
            item = Path(root) / name
            if _is_link(item):
                found.append(record(item))
                directories.remove(name)
        found.extend(record(Path(root) / name) for name in files)
    return sorted(found)


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
    output = build["output"]
    if "{mainBinaryName}" in output or "{productName}" in output:
        try:
            config = json.loads((folder / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
            for field in ("mainBinaryName", "productName"):
                if "{" + field + "}" in output:
                    value = config[field]
                    if not isinstance(value, str) or not value or value in (".", "..") or "/" in value or "\\" in value:
                        raise ValueError(f"invalid {field}")
                    output = output.replace("{" + field + "}", value)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"check": check, "ok": False, "detail": f"cannot determine build output: {exc}", **note}
    output_path = folder / output
    before_build: list[tuple[str, int, int, str]] | None = None
    for index, argv in enumerate(steps):
        # Checked after the first (install) step and before every later one, so a fake tool never runs even once.
        if (index or len(steps) == 1) and build.get("tool_package"):
            problem = _tool_problem(folder, build["tool_package"], build["tool_bin"])
            if problem:
                return {"check": check, "ok": False, "detail": f"not built: {problem}", "command": argv, **note}
        if argv is steps[-1] and output and not output_path.resolve().is_relative_to(folder.resolve()):
            return {"check": check, "ok": False, "detail": f"{output} points outside the app folder", "command": argv, **note}
        if argv is steps[-1] and output and output_path.exists():
            try:
                before_build = _snapshot(output_path)
            except OSError as exc:
                return {"check": check, "ok": False, "detail": f"could not read {output} before the build: {exc}", "command": argv, **note}
        # Found just before it runs, so a setup step can make a tool that a later step uses.
        executable = make_checks._command(argv[0], [], folder)
        if executable is None:
            return {"check": check, "ok": None, "detail": f"not built: {argv[0]} not found (install: {build['install']})", **note}
        # Windows runs .cmd/.bat files (npm, npx) through cmd.exe, which would read these characters as commands.
        if executable[0].lower().endswith((".cmd", ".bat")) and any(set(word) & set('&|^<>%!"') for word in [executable[0], *argv]):
            return {"check": check, "ok": False, "detail": f"not built: `{' '.join(argv)}` has characters cmd.exe would run", **note}
        outcome = make_checks.build([*executable, *argv[1:]], folder, timeout, env)
        if not outcome["ok"]:
            step = "build" if argv is steps[-1] else "setup step"
            return {"check": check, **outcome, "detail": f"{step} `{' '.join(argv)}` failed: {outcome['detail']}",
                    "command": argv, **note}
    if output and not output_path.resolve().is_relative_to(folder.resolve()):
        return {"check": check, "ok": False, "detail": f"{output} points outside the app folder", "command": steps[-1], **note}
    if output and not output_path.exists():
        return {"check": check, "ok": False, "detail": f"build finished but {output} is missing", "command": steps[-1], **note}
    # Output that was there before the build ran, and that the build left alone, was made by setup or the model, not built.
    try:
        unchanged = before_build is not None and _snapshot(output_path) == before_build
    except OSError as exc:
        return {"check": check, "ok": False, "detail": f"could not read {output} after the build: {exc}", "command": steps[-1], **note}
    if unchanged:
        return {"check": check, "ok": False, "detail": f"setup made {output} before the build ran", "command": steps[-1], **note}
    return {"check": check, **outcome, "command": steps[-1], **note}
