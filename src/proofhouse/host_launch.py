"""Host-mode multi-part launch: validate launch.json, check parts, deliver and README."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

from . import make_checks

_PICTURE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})
_VIDEO_SUFFIXES = frozenset({".mp4", ".webm", ".mov", ".mkv"})
_SOUND_SUFFIXES = frozenset({".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".opus"})

LAUNCH_PART_KINDS = frozenset({
    "site", "app", "mcp", "hook", "rule", "skill", "agent", "prompt", "copy", "video",
})
_TEXT_FILE_SUFFIXES = frozenset({".md", ".txt", ".html", ".htm", ".json", ".js", ".py", ".css"})
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_STRIP_TAGS = re.compile(r"<[^>]+>")


class HostError(Exception):
    """A host-mode launch command cannot run; the message says why."""


def _path_inside(folder: Path, name: str) -> Path:
    if not name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
        raise HostError(f"path must stay inside the folder: {name!r}")
    if not make_checks.safe_name(name):
        raise HostError(f"unsafe path: {name!r}")
    path = (folder / name).resolve()
    root = folder.resolve()
    if path.is_symlink() or not path.is_relative_to(root):
        raise HostError(f"path must stay inside the folder: {name!r}")
    return path


def _scan_folder_paths(folder: Path) -> None:
    root = folder.resolve()
    if not folder.is_dir():
        raise HostError(f"folder not found: {folder}")
    for item in folder.rglob("*"):
        if item.is_symlink():
            raise HostError(f"symbolic link not allowed: {item.name}")
        try:
            if item.is_file() and item.stat().st_nlink > 1:
                raise HostError(f"hard link not allowed: {item.name} (copy the file instead)")
        except OSError:
            continue
        try:
            resolved = item.resolve()
        except OSError:
            continue
        if not resolved.is_relative_to(root):
            raise HostError(f"path escapes the folder: {item.name}")


def _read_launch(folder: Path) -> dict[str, Any]:
    manifest = folder / "launch.json"
    if not manifest.is_file():
        raise HostError(f"launch.json not found in {folder}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HostError(f"launch.json in {folder} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise HostError(f"launch.json in {folder} must be a JSON object")
    return data


def _validate_launch_json(folder: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    name, goal = data.get("name"), data.get("goal")
    ok = bool(isinstance(name, str) and name.strip() and isinstance(goal, str) and goal.strip())
    rows.append({"check": "launch.json", "ok": ok, "detail": "" if ok else "name and goal are required"})
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list) or len(raw_parts) < 2:
        rows.append({"check": "launch parts", "ok": False, "detail": "need at least 2 parts"})
        return rows
    rows.append({"check": "launch parts", "ok": True, "detail": f"{len(raw_parts)} parts"})
    seen: set[str] = set()
    for index, raw in enumerate(raw_parts, start=1):
        if not isinstance(raw, dict):
            rows.append({"check": f"part {index}", "ok": False, "detail": "not an object"})
            continue
        part_id = raw.get("id")
        kind = raw.get("kind")
        path_name = raw.get("path")
        if not isinstance(part_id, str) or not part_id.strip():
            rows.append({"check": f"part {index}", "ok": False, "detail": "missing id"})
            continue
        if part_id in seen:
            rows.append({"check": "part ids", "ok": False, "detail": f"duplicate id {part_id!r}"})
            continue
        seen.add(part_id)
        if kind not in LAUNCH_PART_KINDS:
            rows.append({"check": f"part {part_id}", "ok": False, "detail": f"unknown kind {kind!r}"})
            continue
        if not isinstance(path_name, str) or not path_name.strip():
            rows.append({"check": f"part {part_id}", "ok": False, "detail": "missing path"})
            continue
        try:
            resolved = _path_inside(folder, path_name)
        except HostError as exc:
            rows.append({"check": f"part {part_id}", "ok": False, "detail": str(exc)})
            continue
        if kind in ("site", "app", "mcp", "hook", "skill", "video"):
            if not resolved.is_dir():
                rows.append({"check": f"part {part_id}", "ok": False, "detail": f"folder not found: {path_name}"})
        elif not resolved.is_file():
            rows.append({"check": f"part {part_id}", "ok": False, "detail": f"file not found: {path_name}"})
    return rows


def _part_path(folder: Path, raw: dict[str, Any]) -> Path:
    path_name = raw.get("path")
    if not isinstance(path_name, str):
        raise HostError("part path missing")
    return _path_inside(folder, path_name)


def _html_to_text(source: str) -> str:
    stripped = _TAG_RE.sub(" ", source)
    stripped = _STRIP_TAGS.sub(" ", stripped)
    return html.unescape(re.sub(r"\s+", " ", stripped)).strip()


def _collect_part_text(kind: str, path: Path) -> str:
    chunks: list[str] = []
    if kind in ("site", "app"):
        if path.is_dir():
            for file in sorted(path.rglob("*.html")):
                try:
                    chunks.append(_html_to_text(file.read_text(encoding="utf-8")))
                except OSError:
                    continue
        return "\n".join(chunks)
    if kind in ("copy", "prompt", "agent", "rule"):
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return ""
    if kind == "skill":
        skill_md = path / "SKILL.md"
        return skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
    if kind == "video":
        script_path = path / "script.json"
        if not script_path.is_file():
            return ""
        try:
            data = json.loads(script_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        if not isinstance(data, dict):
            return ""
        chunks.append(str(data.get("title", "")))
        chunks.append(str(data.get("voiceover", "")))
        shots = data.get("shots")
        if isinstance(shots, list):
            for shot in shots:
                if isinstance(shot, dict):
                    chunks.append(str(shot.get("caption", "")))
        return "\n".join(chunks)
    if kind in ("mcp", "hook") and path.is_dir():
        for file in sorted(path.rglob("*")):
            if file.is_file() and file.suffix.lower() in _TEXT_FILE_SUFFIXES:
                try:
                    chunks.append(file.read_text(encoding="utf-8"))
                except OSError:
                    continue
    return "\n".join(chunks)


def _consistency_checks(data: dict[str, Any], folder: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list):
        return rows
    part_texts: dict[str, str] = {}
    for raw in raw_parts:
        if not isinstance(raw, dict):
            continue
        part_id = raw.get("id")
        kind = raw.get("kind")
        if not isinstance(part_id, str) or kind not in LAUNCH_PART_KINDS:
            continue
        try:
            path = _part_path(folder, raw)
        except HostError:
            continue
        part_texts[part_id] = _collect_part_text(str(kind), path)

    shared = data.get("shared_names")
    if isinstance(shared, list):
        for name in shared:
            if not isinstance(name, str) or not name.strip():
                continue
            needle = name.casefold()
            for part_id, text in part_texts.items():
                if not text.strip():
                    continue
                if needle not in text.casefold():
                    rows.append({
                        "check": "shared name",
                        "ok": False,
                        "detail": f"{name!r} missing in part {part_id}",
                    })

    facts = data.get("facts")
    if isinstance(facts, list):
        combined = "\n".join(part_texts.values()).casefold()
        for fact in facts:
            if not isinstance(fact, str) or not fact.strip():
                continue
            if fact.casefold() not in combined:
                rows.append({"check": "fact", "ok": False, "detail": f"{fact!r} not found in any part"})

    avoid = data.get("avoid")
    if isinstance(avoid, list):
        for word in avoid:
            if not isinstance(word, str) or not word.strip():
                continue
            needle = word.casefold()
            for part_id, text in part_texts.items():
                if needle in text.casefold():
                    rows.append({
                        "check": "avoid",
                        "ok": False,
                        "detail": f"{word!r} found in part {part_id}",
                    })
                    break

    if not any(row["check"] == "shared name" and row["ok"] is False for row in rows):
        if isinstance(shared, list) and any(isinstance(n, str) and n.strip() for n in shared):
            rows.append({"check": "shared names", "ok": True, "detail": ""})
    if isinstance(facts, list) and facts and not any(row["check"] == "fact" and row["ok"] is False for row in rows):
        rows.append({"check": "facts", "ok": True, "detail": ""})
    if isinstance(avoid, list) and avoid and not any(row["check"] == "avoid" and row["ok"] is False for row in rows):
        rows.append({"check": "avoid", "ok": True, "detail": ""})
    return rows


def _video_structural_checks(folder: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    script_path = folder / "script.json"
    if not script_path.is_file():
        return [{"check": "video script.json", "ok": False, "detail": "not found"}]
    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [{"check": "video script.json", "ok": False, "detail": "invalid JSON"}]
    if not isinstance(data, dict):
        return [{"check": "video script.json", "ok": False, "detail": "must be an object"}]
    for field in ("title", "voiceover", "music"):
        value = data.get(field)
        ok = bool(isinstance(value, str) and value.strip())
        rows.append({"check": f"video {field}", "ok": ok, "detail": "" if ok else "required"})
    raw_shots = data.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        rows.append({"check": "video shots", "ok": False, "detail": "need at least one shot"})
        return rows
    for index, raw in enumerate(raw_shots, start=1):
        if not isinstance(raw, dict):
            rows.append({"check": f"video shot {index}", "ok": False, "detail": "not an object"})
            continue
        try:
            seconds = float(raw.get("seconds", 0))
        except (TypeError, ValueError):
            seconds = 0
        fields_ok = seconds > 0 and all(
            isinstance(raw.get(key), str) and str(raw.get(key)).strip() for key in ("visual", "caption", "file")
        )
        if not fields_ok:
            rows.append({"check": f"video shot {index}", "ok": False, "detail": "needs seconds>0, visual, caption, file"})
            continue
        file_name = str(raw.get("file"))
        try:
            media = _path_inside(folder, file_name)
        except HostError as exc:
            rows.append({"check": f"video shot {index}", "ok": False, "detail": str(exc)})
            continue
        if not media.is_file():
            rows.append({"check": f"video shot {index}", "ok": False, "detail": f"shot file not found: {file_name}"})
            continue
        suffix = PurePosixPath(file_name).suffix.lower()
        if suffix not in _PICTURE_SUFFIXES | _VIDEO_SUFFIXES:
            rows.append({"check": f"video shot {index}", "ok": False, "detail": f"unsupported shot file: {file_name}"})
    for key, label in (("voice_file", "voice"), ("music_file", "music")):
        name = data.get(key)
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            media = _path_inside(folder, name)
        except HostError as exc:
            rows.append({"check": f"video {label} file", "ok": False, "detail": str(exc)})
            continue
        if not media.is_file():
            rows.append({"check": f"video {label} file", "ok": False, "detail": f"not found: {name}"})
        elif PurePosixPath(name).suffix.lower() not in _SOUND_SUFFIXES:
            rows.append({"check": f"video {label} file", "ok": False, "detail": f"unsupported: {name}"})
    if not any(row.get("ok") is False for row in rows):
        rows.append({"check": "video structure", "ok": True, "detail": ""})
    return rows


def collect_launch_checks(folder: Path, *, allow_commands: bool) -> list[dict[str, Any]]:
    from .host import collect_checks

    if not folder.is_dir():
        raise HostError(f"folder not found: {folder}")
    _scan_folder_paths(folder)
    data = _read_launch(folder)
    checks = _validate_launch_json(folder, data)
    if any(row.get("ok") is False for row in checks if row["check"] in ("launch.json", "launch parts", "part ids")):
        return checks
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list):
        return checks
    for raw in raw_parts:
        if not isinstance(raw, dict):
            continue
        part_id = raw.get("id")
        kind = raw.get("kind")
        if not isinstance(part_id, str) or kind not in LAUNCH_PART_KINDS:
            continue
        if any(row.get("ok") is False and row.get("check", "").startswith(f"part {part_id}") for row in checks):
            continue
        try:
            path = _part_path(folder, raw)
        except HostError:
            continue
        if kind == "video":
            part_rows = _video_structural_checks(path)
        else:
            try:
                part_rows = collect_checks(str(kind), path, allow_commands=allow_commands)
            except (HostError, OSError, ValueError) as exc:
                part_rows = [{"check": f"part {part_id}", "ok": False, "detail": str(exc)}]
        for row in part_rows:
            checks.append({
                "check": f"part {part_id}: {row.get('check', '')}",
                "ok": row.get("ok"),
                "detail": row.get("detail", ""),
            })
    checks.extend(_consistency_checks(data, folder))
    return checks


def launch_commands_required(checks: list[dict[str, Any]], folder: Path) -> bool:
    try:
        data = _read_launch(folder)
    except HostError:
        return False
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list):
        return False
    for raw in raw_parts:
        if not isinstance(raw, dict) or raw.get("kind") not in ("mcp", "hook"):
            continue
        part_id = raw.get("id")
        if not isinstance(part_id, str):
            continue
        prefix = f"part {part_id}:"
        part_rows = [row for row in checks if str(row.get("check", "")).startswith(prefix)]
        if any(row.get("ok") is None for row in part_rows):
            return True
    return False


def _part_text_for_readme(kind: str, path: Path) -> str:
    return _collect_part_text(kind, path)


def _part_passed(checks: list[dict[str, Any]], part_id: str) -> bool:
    prefix = f"part {part_id}:"
    part_rows = [row for row in checks if str(row.get("check", "")).startswith(prefix)]
    if not part_rows:
        return False
    return all(row.get("ok") is not False for row in part_rows) and not any(row.get("ok") is None for row in part_rows)


def _fact_carriers(data: dict[str, Any], folder: Path) -> dict[str, list[str]]:
    carriers: dict[str, list[str]] = {}
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list):
        return carriers
    facts = data.get("facts")
    if not isinstance(facts, list):
        return carriers
    for fact in facts:
        if not isinstance(fact, str) or not fact.strip():
            continue
        found: list[str] = []
        needle = fact.casefold()
        for raw in raw_parts:
            if not isinstance(raw, dict):
                continue
            part_id = raw.get("id")
            kind = raw.get("kind")
            if not isinstance(part_id, str) or kind not in LAUNCH_PART_KINDS:
                continue
            try:
                path = _part_path(folder, raw)
            except HostError:
                continue
            if needle in _collect_part_text(str(kind), path).casefold():
                found.append(part_id)
        carriers[fact] = found
    return carriers


def write_launch_readme(
    readme_path: Path,
    data: dict[str, Any],
    folder: Path,
    checks: list[dict[str, Any]],
    *,
    agent: str,
    score: int | None,
) -> None:
    lines = [
        f"# {data.get('name', 'Launch')}",
        "",
        f"**Goal:** {data.get('goal', '')}",
        "",
        "## Parts",
        "",
        "| id | kind | path | check |",
        "| --- | --- | --- | --- |",
    ]
    raw_parts = data.get("parts")
    if isinstance(raw_parts, list):
        for raw in raw_parts:
            if not isinstance(raw, dict):
                continue
            part_id = str(raw.get("id", ""))
            kind = str(raw.get("kind", ""))
            path_name = str(raw.get("path", ""))
            status = "passed" if _part_passed(checks, part_id) else "failed"
            lines.append(f"| {part_id} | {kind} | {path_name} | {status} |")
    lines.extend(["", "## Shared names", ""])
    shared = data.get("shared_names")
    if isinstance(shared, list):
        for name in shared:
            if isinstance(name, str) and name.strip():
                lines.append(f"- {name}")
    lines.extend(["", "## Facts (which part carried each)", ""])
    for fact, parts in _fact_carriers(data, folder).items():
        where = ", ".join(parts) if parts else "none"
        lines.append(f"- {fact}: {where}")
    lines.extend(["", "## Record", "", f"- Agent: {agent}", f"- Score: {score if score is not None else 'n/a'}", ""])
    readme_path.write_text("\n".join(lines), encoding="utf-8")


def _copytree_contents(source: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = dest / child.name
        if child.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def save_launch_version(out: Path, version: int, source: Path) -> Path:
    version_dir = out / f"v{version}"
    if version_dir.exists():
        shutil.rmtree(version_dir)
    _copytree_contents(source, version_dir)
    return version_dir


def load_launch_source(source: Path) -> str:
    _scan_folder_paths(source)
    _read_launch(source)
    return (source / "launch.json").read_text(encoding="utf-8")


def _read_manifest(folder: Path) -> dict[str, Any]:
    manifest = folder / "manifest.json"
    if not manifest.is_file():
        raise HostError(f"manifest.json not found in {folder}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HostError(f"manifest.json in {folder} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise HostError(f"manifest.json in {folder} must be a JSON object")
    return data


def _copy_support_files(source: Path, dest: Path) -> None:
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        if item.is_file() and relative.as_posix() != "SKILL.md":
            (dest / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest / relative)


def _deliver_part(dest: Path, kind: str, source: Path, text: str, request: str) -> None:
    if kind in ("site", "app", "mcp", "hook", "video"):
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
        if kind == "mcp":
            from .hosts import check_name
            from .make import _slug

            data = _read_manifest(dest)
            try:
                name = check_name(data["name"])
            except (KeyError, ValueError):
                name = _slug(request)
            command, args = data.get("command"), data.get("args")
            if isinstance(command, str) and isinstance(args, list) and all(isinstance(a, str) for a in args):
                line = make_checks.install_line(name, command, args, dest)
                if line is not None:
                    (dest.parent / f"{dest.name}-INSTALL-MCP.txt").write_text(line + "\n", encoding="utf-8")
        elif kind == "hook":
            data = _read_manifest(dest)
            event, command, matcher = data.get("event"), data.get("command"), data.get("matcher")
            if isinstance(event, str) and isinstance(command, str):
                snippet = make_checks.settings_snippet(
                    event, matcher if isinstance(matcher, str) else None, command, dest,
                )
                if snippet is not None:
                    (dest.parent / f"{dest.name}-settings-snippet.json").write_text(
                        json.dumps(snippet, indent=2) + "\n", encoding="utf-8",
                    )
        return
    if kind == "skill":
        dest.mkdir(parents=True, exist_ok=True)
        skill_dest = dest / source.name
        if skill_dest.exists():
            shutil.rmtree(skill_dest)
        shutil.copytree(source, skill_dest)
        _copy_support_files(source, skill_dest)
        return
    if kind in ("copy", "prompt"):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "final.md").write_text(text.rstrip("\n") + "\n", encoding="utf-8")
        return
    if kind == "agent":
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest / source.name)
        return
    if kind == "rule":
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest / source.name)


def deliver_launch(out: Path, version_dir: Path, checks: list[dict[str, Any]], *, agent: str, score: int | None, request: str) -> list[str]:
    data = _read_launch(version_dir)
    shutil.copy2(version_dir / "launch.json", out / "launch.json")
    delivered: list[str] = ["launch.json"]
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list):
        return delivered
    for raw in raw_parts:
        if not isinstance(raw, dict):
            continue
        part_id = raw.get("id")
        kind = raw.get("kind")
        if not isinstance(part_id, str) or kind not in LAUNCH_PART_KINDS:
            continue
        path = _part_path(version_dir, raw)
        text = ""
        if kind in ("copy", "prompt", "agent", "rule") and path.is_file():
            text = path.read_text(encoding="utf-8")
        elif kind == "skill" and (path / "SKILL.md").is_file():
            text = (path / "SKILL.md").read_text(encoding="utf-8")
        dest = out / part_id
        _deliver_part(dest, str(kind), path, text, request)
        delivered.append(part_id)
    write_launch_readme(out / "README.md", data, version_dir, checks, agent=agent, score=score)
    delivered.append("README.md")
    return delivered
