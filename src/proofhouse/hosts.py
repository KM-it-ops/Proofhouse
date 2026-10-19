"""Put agents, rules and MCP servers into the tools you work in, and take them out again cleanly.

A host (Claude Code, Cursor, Codex, or any tool you add) is data: for each kind
of item it names the file Proofhouse writes, at user level (``~``) or inside a
project (``{project}``), and how it writes it:

- ``file``: a whole file of its own (a Claude Code subagent, a Cursor rule).
- ``md-block``: a marked block inside a shared Markdown file (``CLAUDE.md``,
  ``AGENTS.md``); everything outside the block is left alone.
- ``json-mcp``: one entry under ``mcpServers`` in a JSON file; other entries
  are left alone.
- ``toml-block``: a marked ``[mcp_servers.<name>]`` block in a TOML file.

Every install keeps a record under ``PROOFHOUSE_HOME/installs`` and a copy of
any file it changes, so installing twice changes nothing and an uninstall
removes only what Proofhouse wrote. If you edited it since, the uninstall
refuses unless ``force``. Names are lowercase words joined by hyphens, so a
name can never point outside the target folder.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .optimize.kinds import is_link
from .providers import proofhouse_home, write_atomic

HOSTS_SCHEMA = "proofhouse.hosts/v1"
SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "hosts.json"
KINDS = ("agent", "rule", "mcp")
FORMATS = ("file", "md-block", "json-mcp", "toml-block")
_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


class HostError(ValueError):
    """The install or uninstall cannot go ahead; nothing was changed."""


@dataclass(frozen=True, slots=True)
class Target:
    host: str
    host_name: str
    kind: str
    name: str
    path: Path
    format: str


def _read_hosts(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise HostError(f"{path} is unreadable: {type(exc).__name__}") from None
    if not isinstance(data, dict) or data.get("schema") != HOSTS_SCHEMA or not isinstance(data.get("hosts"), list):
        raise HostError(f"{path} must be a {HOSTS_SCHEMA} file with a hosts list")
    return _check_hosts(data["hosts"], str(path))


def _check_hosts(found: list[Any], where: str) -> list[dict[str, Any]]:
    for host in found:
        if not isinstance(host, dict) or not isinstance(host.get("id"), str) or not _NAME.fullmatch(host["id"]):
            raise HostError(f"{where}: every host needs an id of lowercase words joined by hyphens")
        for kind in KINDS:
            spec = host.get(kind)
            if spec is not None and (not isinstance(spec, dict) or spec.get("format") not in FORMATS):
                raise HostError(f"{where}: host {host['id']} {kind} needs a format, one of {', '.join(FORMATS)}")
    return found


def all_hosts() -> dict[str, dict[str, Any]]:
    """Shipped hosts, then add-ons, then yours (``PROOFHOUSE_HOME/hosts.json``); a later one with the same id replaces it."""
    from . import addons

    found = {host["id"]: host for host in _read_hosts(SHIPPED_PATH)}
    for name, host in addons.contributions("hosts"):
        try:
            found.update({h["id"]: h for h in _check_hosts([host], f"add-on {name}")})
        except HostError:
            continue  # checked when the pack was installed; a package add-on's bad entry is skipped
    found.update({host["id"]: host for host in _read_hosts(proofhouse_home() / "hosts.json")})
    return found


def check_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise HostError(f"name {name!r} must be lowercase letters, digits and hyphens (for example review-bot)")
    return name


def target(host_id: str, kind: str, name: str, project: Path | None) -> Target:
    if kind not in KINDS:
        raise HostError(f"kind must be one of {', '.join(KINDS)}")
    host = all_hosts().get(host_id)
    if host is None:
        raise HostError(f"no tool named {host_id!r}; known: {', '.join(sorted(all_hosts()))} (add one in {proofhouse_home() / 'hosts.json'})")
    spec = host.get(kind)
    label = host.get("name", host_id)
    if spec is None:
        raise HostError(f"{label} has no place for {kind}s")
    template = spec.get("project") if project is not None else spec.get("user")
    if template is None:
        where = "a project (--project DIR)" if project is None else "your user settings (leave out --project)"
        raise HostError(f"{label} keeps {kind}s only in {where}")
    if project is not None:
        root = project.resolve()
        text = template.replace("{project}", str(root))
    else:
        root = Path.home().resolve()
        text = str(root) + template[1:] if template.startswith("~") else template
    path = Path(text.replace("{name}", check_name(name)))
    if not path.is_absolute():
        path = root / path
    path = Path(os.path.normpath(path))  # fold ".." before the check; links are refused below, not followed
    try:
        path.relative_to(root)
    except ValueError:
        raise HostError(f"{path} is outside {root}") from None
    _refuse_links(path)
    return Target(host_id, label, kind, name, path, spec["format"])


# --- records -----------------------------------------------------------------------------------


def _refuse_links(path: Path) -> None:
    """Refuse a symlink or junction on ``path`` or any parent short of the drive root.

    Opening the path would follow it, so a ``CLAUDE.md`` that points at another
    file would be overwritten. A link cannot be backed up and put back as a link.
    Nothing is changed.
    """
    current = path
    while current.parent != current:
        if os.path.lexists(current) and is_link(current):
            raise HostError(
                f"{current} is a link or junction; remove or replace it yourself, then install again. Nothing was changed."
            )
        current = current.parent


def _record_path(t: Target) -> Path:
    key = hashlib.sha256(str(t.path).encode("utf-8")).hexdigest()[:12]
    return proofhouse_home() / "installs" / f"{t.host}-{t.kind}-{t.name}-{key}.json"


def _write(path: Path, content: str | bytes) -> None:
    write_atomic(path, content)


def _backup(t: Target) -> str | None:
    if not t.path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    copy = proofhouse_home() / "install-backups" / f"{t.host}-{t.kind}-{t.name}-{stamp}{t.path.suffix}"
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(t.path, copy)
    return str(copy)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- blocks ------------------------------------------------------------------------------------


def _markers(t: Target) -> tuple[str, str]:
    if t.format == "toml-block":
        return f"# proofhouse:begin {t.name}", f"# proofhouse:end {t.name}"
    return f"<!-- proofhouse:begin {t.name} -->", f"<!-- proofhouse:end {t.name} -->"


def _find_block(text: str, t: Target) -> tuple[int, int] | None:
    begin, end = _markers(t)
    start = text.find(begin)
    if start < 0:
        return None
    stop = text.find(end, start)
    if stop < 0:
        raise HostError(f"{t.path} has the start of a Proofhouse block for {t.name} but no end; fix it by hand first")
    return start, stop + len(end) + (1 if text[stop + len(end): stop + len(end) + 1] == "\n" else 0)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(json.dumps(str(v)) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{json.dumps(str(k))} = {json.dumps(str(v))}" for k, v in value.items()) + " }"
    raise HostError(f"cannot write {type(value).__name__} into TOML")


def _block_body(t: Target, content: Any) -> str:
    begin, end = _markers(t)
    if t.format == "toml-block":
        lines = [f"[mcp_servers.{t.name}]"] + [f"{key} = {_toml_value(value)}" for key, value in content.items()]
        body = "\n".join(lines)
    else:
        body = str(content).strip()
    return f"{begin}\n{body}\n{end}\n"


# --- install / uninstall -----------------------------------------------------------------------


def install(t: Target, content: Any, *, force: bool = False) -> str:
    """Write ``content`` for ``t``. Returns what happened in one line."""
    _refuse_links(t.path)
    record_file = _record_path(t)
    record = json.loads(record_file.read_text(encoding="utf-8")) if record_file.is_file() else None
    existing = t.path.read_text(encoding="utf-8") if t.path.is_file() else None
    before = t.path.read_bytes() if existing is not None else None

    if t.format == "file":
        text = str(content).rstrip("\n") + "\n"
        if existing == text:
            return f"{t.path} already holds this {t.kind}; nothing changed"
        if existing is not None and record is None and not force:
            raise HostError(f"{t.path} exists and was not written by Proofhouse; use --force to replace it (a copy is kept)")
        if existing is not None and record is not None and _digest(existing) != record["digest"] and not force:
            raise HostError(f"{t.path} changed since Proofhouse wrote it; use --force to replace it (a copy is kept)")
        backup = _backup(t) if record is None else record.get("backup")
        _write(t.path, text)
        written = text
    elif t.format in ("md-block", "toml-block"):
        if t.format == "toml-block" and existing and re.search(rf"^\[mcp_servers\.{re.escape(t.name)}\]", existing, re.M):
            if _find_block(existing, t) is None and not force:
                raise HostError(f"{t.path} already defines mcp_servers.{t.name} outside Proofhouse; use --force or pick another name")
        block = _block_body(t, content)
        current = existing or ""
        span = _find_block(current, t)
        new_text = current[: span[0]] + block + current[span[1]:] if span else current + ("\n" if current and not current.endswith("\n\n") else "") + block
        if new_text == current:
            return f"{t.path} already holds this {t.kind}; nothing changed"
        backup = _backup(t) if record is None else record.get("backup")
        _write(t.path, new_text)
        written = block
    elif t.format == "json-mcp":
        try:
            data = json.loads(existing) if existing else {}
        except ValueError:
            raise HostError(f"{t.path} is not valid JSON; fix it by hand first") from None
        if not isinstance(data, dict) or not isinstance(data.setdefault("mcpServers", {}), dict):
            raise HostError(f"{t.path} does not hold an mcpServers object")
        current = data["mcpServers"].get(t.name)
        if current == content:
            return f"{t.path} already holds this {t.kind}; nothing changed"
        if current is not None and record is None and not force:
            raise HostError(f"{t.path} already has an MCP server named {t.name}; use --force or pick another name")
        backup = _backup(t) if record is None else record.get("backup")
        data["mcpServers"][t.name] = content
        _write(t.path, json.dumps(data, indent=2) + "\n")
        written = content
    else:
        raise HostError(f"unknown format {t.format}")

    try:
        _write(record_file, json.dumps({
            "schema": "proofhouse.host-install/v1", "host": t.host, "kind": t.kind, "name": t.name, "path": str(t.path),
            "format": t.format, "written": written, "digest": _digest(written if isinstance(written, str) else json.dumps(written, sort_keys=True)),
            "created_file": existing is None if record is None else record.get("created_file", False), "backup": backup,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2, sort_keys=True) + "\n")
    except OSError:
        # without its record the install could not be undone cleanly, so put the tool's file back as it was
        if before is None:
            t.path.unlink(missing_ok=True)
        else:
            _write(t.path, before)
        if record is None and backup:
            Path(backup).unlink(missing_ok=True)
        raise
    return f"installed {t.kind} {t.name} into {t.host_name}: {t.path}"


def uninstall(t: Target, *, force: bool = False) -> str:
    _refuse_links(t.path)
    record_file = _record_path(t)
    if not record_file.is_file():
        raise HostError(f"Proofhouse has no record of installing {t.kind} {t.name} into {t.host_name} at {t.path}")
    record = json.loads(record_file.read_text(encoding="utf-8"))
    existing = t.path.read_text(encoding="utf-8") if t.path.is_file() else None
    if existing is None:
        record_file.unlink()
        return f"{t.path} is already gone; record removed"

    if t.format == "file":
        if _digest(existing) != record["digest"] and not force:
            raise HostError(f"{t.path} changed since Proofhouse wrote it; use --force to remove it anyway")
        backup = record.get("backup")
        if backup and Path(backup).is_file():
            _write(t.path, Path(backup).read_bytes())
        else:
            t.path.unlink()
    elif t.format in ("md-block", "toml-block"):
        span = _find_block(existing, t)
        if span is None:
            raise HostError(f"{t.path} no longer holds the Proofhouse block for {t.name}; nothing removed")
        if existing[span[0]: span[1]] != record["written"] and not force:
            raise HostError(f"the {t.name} block in {t.path} changed since Proofhouse wrote it; use --force to remove it anyway")
        remaining = existing[: span[0]] + existing[span[1]:]
        if record.get("created_file") and not remaining.strip():
            t.path.unlink()
        else:
            _write(t.path, remaining.rstrip("\n") + "\n" if remaining.strip() else "")
    else:  # json-mcp
        data = json.loads(existing)
        servers = data.get("mcpServers", {})
        if servers.get(t.name) != record["written"] and not force:
            raise HostError(f"the MCP server {t.name} in {t.path} changed since Proofhouse wrote it; use --force to remove it anyway")
        servers.pop(t.name, None)
        if record.get("created_file") and not servers and set(data) == {"mcpServers"}:
            t.path.unlink()
        else:
            _write(t.path, json.dumps(data, indent=2) + "\n")
    record_file.unlink()
    return f"removed {t.kind} {t.name} from {t.host_name}: {t.path}"
