"""Host mode: the person's AI app writes and judges; Proofhouse checks, records and assembles."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__, app_platforms, hosts, make, make_checks, sitecheck, studio
from . import host_quality
from .optimize.install_skill import check_frontmatter

CHECK_KINDS = ("site", "app", "mcp", "hook", "rule", "skill", "agent", "prompt", "copy", "launch")
RECORD_KINDS = CHECK_KINDS
_TEXT_KINDS = ("prompt", "copy")
# Filler that finished writing must not still contain (a prompt may keep {{variables}}).
_FILLER = re.compile(r"lorem ipsum|\[\s*(?:insert|your|add|company|name)\b[^\]]*\]|\bTBD\b|\bTODO\b", re.IGNORECASE)
JUDGE_NOTE = (
    "Scores are the agent's own advice because the same model wrote the work and scored it; "
    "they are not proof. If you have a second agent (for example Codex or Gemini CLI), ask it to "
    "judge a version and record that score instead."
)


def agent_base(name: str) -> str:
    base, _, _ = name.partition(":")
    return base.strip().casefold()


def judge_note_for_record(agent: str, judge: str | None) -> str:
    if judge:
        return (
            f"Scored by {judge}, a different agent from the writer ({agent}); still advice, not proof."
        )
    return JUDGE_NOTE
_VIDEO_SUFFIX = re.compile(r"\.(mp4|webm|mov|mkv)$", re.IGNORECASE)
_PICTURE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})
_VIDEO_SUFFIXES = frozenset({".mp4", ".webm", ".mov", ".mkv"})
_SOUND_SUFFIXES = frozenset({".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".opus"})


class HostError(Exception):
    """A host-mode command cannot run; the message says why."""


def _print_error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def _check_rows_pass_exit(checks: list[dict[str, Any]], *, commands_required: bool) -> int:
    if any(row.get("ok") is False for row in checks):
        return 1
    if commands_required and any(row.get("ok") is None for row in checks):
        return 1
    return 0


def _format_check_line(row: dict[str, Any]) -> str:
    name, detail = row.get("check", ""), str(row.get("detail", "")).strip()
    if row.get("ok") is True:
        return f"PASS: {name}" + (f" ({detail})" if detail else "")
    if row.get("ok") is False:
        return f"FAIL: {name}" + (f": {detail}" if detail else "")
    return f"{name}: {detail}" if detail else name


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


def _require_suffix(name: str, allowed: frozenset[str], what: str) -> None:
    if PurePosixPath(name).suffix.lower() not in allowed:
        raise HostError(f"{what} file type not supported: {name!r} (use {', '.join(sorted(allowed))})")


def _check_out_folder(out: Path, source: Path, kind: str) -> None:
    out_root, source_root = out.resolve(), source.resolve()
    if out_root == source_root or out_root.is_relative_to(source_root) or source_root.is_relative_to(out_root):
        raise HostError("--out must be a separate folder that neither holds nor sits inside the thing you are recording")
    if out.exists() and not out.is_dir():
        raise HostError(f"--out is not a folder: {out}")
    if out.is_dir() and any(out.iterdir()) and not (out / "record.json").is_file():
        raise HostError(f"--out folder is not empty and holds no Proofhouse record: {out} (pick a new or empty folder)")
    held = _read_record(out).get("kind")
    if held and held != kind:
        raise HostError(f"--out already holds a {held} record, not a {kind} one (pick another folder for a different kind)")


def _read_record(out: Path) -> dict[str, Any]:
    try:
        data = json.loads((out / "record.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


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


def _manifest_paths(folder: Path, data: dict[str, Any]) -> list[str]:
    names: list[str] = []
    files = data.get("files")
    if isinstance(files, dict):
        names.extend(str(key) for key in files)
    command, args = data.get("command"), data.get("args")
    if isinstance(command, str) and command.startswith("./"):
        names.append(command[2:])
    if isinstance(args, list):
        for arg in args:
            if isinstance(arg, str) and not arg.startswith("-") and "://" not in arg:
                if make_checks._SCRIPT_SUFFIX.fullmatch(PurePosixPath(arg).suffix):
                    names.append(arg)
    hook_command = data.get("command")
    if isinstance(hook_command, str) and " " in hook_command:
        parts = hook_command.split()
        if parts[0].startswith("./"):
            names.append(parts[0][2:])
        for part in parts[1:]:
            if not part.startswith("-") and "://" not in part and make_checks._SCRIPT_SUFFIX.fullmatch(PurePosixPath(part).suffix):
                names.append(part)
    return names


def run_check(kind: str, path: Path, *, allow_commands: bool, as_json: bool) -> int:
    try:
        checks = collect_checks(kind, path, allow_commands=allow_commands)
    except (HostError, hosts.HostError, OSError, ValueError) as exc:
        _print_error(str(exc))
        return 2
    if as_json:
        print(json.dumps(checks, indent=2))
    else:
        for row in checks:
            print(_format_check_line(row))
    commands_required = kind in ("mcp", "hook")
    if kind == "launch":
        from .host_launch import launch_commands_required

        commands_required = launch_commands_required(checks, path)
    return _check_rows_pass_exit(checks, commands_required=commands_required)


def collect_checks(kind: str, path: Path, *, allow_commands: bool) -> list[dict[str, Any]]:
    if kind == "launch":
        from .host_launch import HostError as LaunchHostError, collect_launch_checks

        try:
            return collect_launch_checks(path, allow_commands=allow_commands)
        except LaunchHostError as exc:
            raise HostError(str(exc)) from exc
    if kind in _TEXT_KINDS:
        if not path.is_file():
            raise HostError(str(path))
        return _text_checks(kind, path.read_text(encoding="utf-8"))
    if kind not in CHECK_KINDS:
        raise HostError(f"unknown kind {kind!r}")
    if not path.exists():
        raise HostError(str(path))
    if kind == "site":
        if not path.is_dir():
            raise HostError(f"folder not found: {path}")
        if not (path / "index.html").is_file():
            raise HostError(f"index.html not found in {path}")
        checks = sitecheck.check_site(path, shots=None, browser=allow_commands)
        checks.extend(host_quality.site_readability_rows(path))
        checks.extend(host_quality.text_quality_rows(host_quality.site_text_from_folder(path), "copy"))
        return checks
    if kind == "app":
        if not path.is_dir():
            raise HostError(f"folder not found: {path}")
        if not (path / "index.html").is_file():
            raise HostError(f"index.html not found in {path}")
        pwa = next(entry for entry in app_platforms.read_shipped() if entry["id"] == "pwa")
        checks = [
            *app_platforms.static_checks(path, pwa),
            *sitecheck.check_site(path, shots=None, browser=allow_commands),
            *host_quality.site_readability_rows(path),
            *host_quality.text_quality_rows(host_quality.site_text_from_folder(path), "copy"),
        ]
        return checks
    if kind == "skill":
        skill_md = path / "SKILL.md"
        if not skill_md.is_file():
            raise HostError(f"SKILL.md not found in {path}")
        text = skill_md.read_text(encoding="utf-8")
        try:
            check_frontmatter(text)
        except Exception as exc:  # noqa: BLE001
            return [{"check": "skill frontmatter", "ok": False, "detail": str(exc)}]
        rows = [{"check": "skill frontmatter", "ok": True, "detail": check_frontmatter(text)}]
        rows.extend(host_quality.text_quality_rows(host_quality.body_after_frontmatter(text), "skill"))
        return rows
    if kind == "agent":
        if not path.is_file():
            raise HostError(str(path))
        text = path.read_text(encoding="utf-8")
        try:
            check_frontmatter(text)
        except Exception as exc:  # noqa: BLE001
            return [{"check": "agent frontmatter", "ok": False, "detail": str(exc)}]
        rows = [{"check": "agent frontmatter", "ok": True, "detail": check_frontmatter(text)}]
        rows.extend(host_quality.text_quality_rows(host_quality.body_after_frontmatter(text), "skill"))
        return rows
    if kind == "rule":
        if not path.is_file():
            raise HostError(str(path))
        text = path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="host-rule-") as temporary:
            folder = Path(temporary)
            _, checks = make_checks.rule(text, path.stem, folder)
        return checks
    if kind in ("mcp", "hook"):
        if not path.is_dir():
            raise HostError(f"folder not found: {path}")
        _scan_folder_paths(path)
        data = _read_manifest(path)
        for name in _manifest_paths(path, data):
            _path_inside(path, name)
        if kind == "mcp":
            return make_checks.mcp(data, path, allow_commands)
        return make_checks.hook(data, path, allow_commands)
    raise HostError(f"unknown kind {kind!r}")


def _text_checks(kind: str, text: str) -> list[dict[str, Any]]:
    found = _FILLER.search(text)
    rows = [
        {"check": f"{kind} present", "ok": bool(text.strip()), "detail": ""},
        {"check": f"{kind} has no filler", "ok": found is None, "detail": f"still contains {found.group(0)!r}" if found else ""},
    ]
    rows.extend(host_quality.text_quality_rows(text, kind))
    return rows


def _next_version(out: Path) -> int:
    highest = 0
    for child in out.iterdir() if out.is_dir() else []:
        if child.is_dir() and child.name.startswith("v") and child.name[1:].isdigit():
            highest = max(highest, int(child.name[1:]))
    return highest + 1


def _version_passed(checks: list[dict[str, Any]], *, commands_required: bool) -> bool:
    return bool(checks) and _check_rows_pass_exit(checks, commands_required=commands_required) == 0


def _pick_best(rounds: list[dict[str, Any]]) -> int | None:
    eligible = [row for row in rounds if row.get("passed")]
    if not eligible:
        return None
    # Judged passing rounds outrank self-scored ones; then judge_score, self score, version.
    any_judged = any(row.get("judge_score") is not None for row in eligible)

    def key(row: dict[str, Any]) -> tuple[Any, ...]:
        judged = row.get("judge_score") is not None
        if any_judged:
            return (
                judged,
                row.get("judge_score") if judged else -1,
                row.get("score") if row.get("score") is not None else -1,
                row["version"],
            )
        return (row.get("score") if row.get("score") is not None else -1, row["version"])

    return max(eligible, key=key)["version"]


def _clear_delivery(out: Path, delivered: list[str]) -> None:
    """Remove only what an earlier delivery put in ``out``; anything the person added stays."""
    for name in delivered:
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            continue
        target = out / name
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target, ignore_errors=True)
        else:
            target.unlink(missing_ok=True)


def _copy_support_files(source: Path, dest: Path) -> None:
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        if item.is_file() and relative.as_posix() != "SKILL.md":
            (dest / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest / relative)


def _deliver_version(out: Path, kind: str, version: int, text: str, request: str) -> None:
    source = out / f"v{version}"
    if kind in ("site", "app"):
        site_src = source / kind
        if site_src.is_dir():
            dest = out / kind
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(site_src, dest)
        return
    if kind in _TEXT_KINDS:
        make._deliver(out, kind, text.rstrip("\n"))
        return
    if kind == "skill":
        before = {path.name for path in out.iterdir()}
        make._deliver(out, kind, text.rstrip("\n"))
        for name in sorted({path.name for path in out.iterdir()} - before):
            if (out / name / "SKILL.md").is_file():
                _copy_support_files(_skill_version_dir(out, version, Path("skill")), out / name)
        return
    if kind == "agent":
        make._deliver(out, kind, text.rstrip("\n"))
        return
    if kind == "rule":
        for path in source.glob("*.md"):
            shutil.copy2(path, out / path.name)
        return
    if kind in ("mcp", "hook"):
        kind_src = source / kind
        if not kind_src.is_dir():
            return
        dest = out / kind
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(kind_src, dest)
        data = _read_manifest(dest)
        if kind == "mcp":
            from .hosts import check_name

            try:
                name = check_name(data["name"])
            except (KeyError, ValueError):
                name = make._slug(request)
            command, args = data.get("command"), data.get("args")
            if isinstance(command, str) and isinstance(args, list) and all(isinstance(a, str) for a in args):
                line = make_checks.install_line(name, command, args, dest)
                if line is not None:
                    (out / "INSTALL-MCP.txt").write_text(make_checks.install_text(line), encoding="utf-8")
        else:
            event, command, matcher = data.get("event"), data.get("command"), data.get("matcher")
            if isinstance(event, str) and isinstance(command, str):
                snippet = make_checks.settings_snippet(event, matcher if isinstance(matcher, str) else None, command, dest)
                if snippet is not None:
                    (out / "settings-snippet.json").write_text(json.dumps(snippet, indent=2) + "\n", encoding="utf-8")
                    note = make_checks.snippet_note(snippet)
                    if note:
                        (out / "INSTALL-HOOK.txt").write_text(note, encoding="utf-8")


def _save_version(out: Path, kind: str, version: int, source: Path, text: str) -> Path:
    version_dir = out / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)
    if kind in ("site", "app"):
        dest = version_dir / kind
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
    elif kind in _TEXT_KINDS:
        (out / f"v{version}.md").write_text(text, encoding="utf-8")
    elif kind == "skill":
        dest = version_dir / source.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
    elif kind == "agent":
        shutil.copy2(source, version_dir / source.name)
    elif kind == "rule":
        shutil.copy2(source, version_dir / source.name)
    elif kind in ("mcp", "hook"):
        dest = version_dir / kind
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
    elif kind == "launch":
        from .host_launch import save_launch_version

        return save_launch_version(out, version, source)
    return version_dir


def _load_source(kind: str, source: Path) -> str:
    if kind in ("site", "app", "skill", "mcp", "hook", "launch") and source.is_dir():
        _scan_folder_paths(source)  # before any copy, so a link never pulls outside files into the record
    if kind in ("site", "app"):
        if not source.is_dir():
            raise HostError(str(source))
        index = source / "index.html"
        if not index.is_file():
            raise HostError(f"index.html not found in {source}")
        return ""
    if kind == "skill":
        skill_md = source / "SKILL.md"
        if not skill_md.is_file():
            raise HostError(f"SKILL.md not found in {source}")
        return skill_md.read_text(encoding="utf-8")
    if kind in ("agent", "rule", *_TEXT_KINDS):
        if not source.is_file():
            raise HostError(str(source))
        if kind not in _TEXT_KINDS and source.suffix.lower() != ".md":
            raise HostError(f"a {kind} file must end in .md: {source.name}")
        return source.read_text(encoding="utf-8")
    if kind in ("mcp", "hook"):
        if not source.is_dir():
            raise HostError(str(source))
        _read_manifest(source)
        return ""
    if kind == "launch":
        from .host_launch import HostError as LaunchHostError, load_launch_source

        try:
            return load_launch_source(source)
        except LaunchHostError as exc:
            raise HostError(str(exc)) from exc
    raise HostError(f"unknown kind {kind!r}")


def run_record(
    kind: str,
    source: Path,
    *,
    out: Path,
    request: str,
    agent: str,
    score: int | None,
    judge: str | None,
    judge_score: int | None,
    judge_note: str | None,
    allow_commands: bool,
    as_json: bool,
) -> int:
    if kind not in RECORD_KINDS:
        _print_error(f"unknown kind {kind!r}")
        return 2
    try:
        text = _load_source(kind, source)
        _check_out_folder(out, source, kind)
        out.mkdir(parents=True, exist_ok=True)
    except (HostError, OSError, ValueError) as exc:
        _print_error(str(exc))
        return 2
    version = _next_version(out)
    try:
        _save_version(out, kind, version, source, text)
        checks = collect_checks(kind, _check_target(out, kind, version, source), allow_commands=allow_commands)
    except (HostError, hosts.HostError, OSError, ValueError) as exc:
        shutil.rmtree(out / f"v{version}", ignore_errors=True)
        (out / f"v{version}.md").unlink(missing_ok=True)
        _print_error(str(exc))
        return 2
    (out / f"v{version}" / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    commands_required = kind in ("mcp", "hook")
    if kind == "launch":
        from .host_launch import launch_commands_required

        commands_required = launch_commands_required(checks, source)
    passed = _version_passed(checks, commands_required=commands_required)
    record_path = out / "record.json"
    prior = _read_record(out)
    rounds: list[dict[str, Any]] = list(prior.get("rounds") or [])
    prior_delivered = [str(name) for name in prior.get("delivered") or []]
    round_row: dict[str, Any] = {"version": version, "score": score, "passed": passed}
    if judge is not None:
        round_row["judge"] = judge
        round_row["judge_score"] = judge_score
        if judge_note:
            round_row["judge_note"] = judge_note
    rounds.append(round_row)
    best_version = _pick_best(rounds)
    best_round = next((row for row in rounds if row.get("version") == best_version), None) if best_version else None
    best_judge = best_round.get("judge") if best_round else None
    payload: dict[str, Any] = {
        "schema": "proofhouse.host/v1",
        "proofhouse_version": __version__,
        "request": request,
        "agent": agent,
        "kind": kind,
        "rounds": rounds,
        "best_version": best_version,
        "judge_note": judge_note_for_record(agent, best_judge),
    }
    if best_round and best_round.get("judge_score") is not None:
        payload["judge"] = best_round.get("judge")
        payload["judge_score"] = best_round.get("judge_score")
    _clear_delivery(out, prior_delivered)
    delivered: list[str] = []
    if best_version is not None:
        before = {path.name for path in out.iterdir()}
        best_text = _version_text(out, kind, best_version, request)
        if kind == "launch":
            from .host_launch import deliver_launch

            version_dir = out / f"v{best_version}"
            best_checks = json.loads((version_dir / "checks.json").read_text(encoding="utf-8"))
            best_score = best_round.get("score") if best_round else score
            delivered = deliver_launch(
                out,
                version_dir,
                best_checks,
                agent=agent,
                score=best_score,
                request=request,
                judge=best_round.get("judge") if best_round else None,
                judge_score=best_round.get("judge_score") if best_round else None,
            )
        else:
            _deliver_version(out, kind, best_version, best_text, request)
            delivered = sorted({path.name for path in out.iterdir()} - before)
    payload["delivered"] = delivered
    record_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    not_run = sum(1 for row in checks if row.get("ok") is None)
    if as_json:
        print(json.dumps({"version": version, "checks_not_run": not_run, "passed": passed, "best_version": best_version}))
    return 0


def _check_target(out: Path, kind: str, version: int, source: Path) -> Path:
    if kind in ("site", "app"):
        return out / f"v{version}" / kind
    if kind == "skill":
        return _skill_version_dir(out, version, source)
    if kind in ("agent", "rule"):
        return next((out / f"v{version}").glob("*.md"))
    if kind in ("mcp", "hook"):
        return out / f"v{version}" / kind
    if kind in _TEXT_KINDS:
        return out / f"v{version}.md"
    if kind == "launch":
        return out / f"v{version}"
    raise HostError(f"unknown kind {kind!r}")


def _skill_version_dir(out: Path, version: int, source: Path) -> Path:
    version_dir = out / f"v{version}"
    for child in version_dir.iterdir():
        if child.is_dir() and (child / "SKILL.md").is_file():
            return child
    return version_dir / source.name


def _version_text(out: Path, kind: str, version: int, request: str) -> str:
    if kind in _TEXT_KINDS:
        return (out / f"v{version}.md").read_text(encoding="utf-8")
    if kind == "skill":
        return (_skill_version_dir(out, version, Path("skill")) / "SKILL.md").read_text(encoding="utf-8")
    if kind == "agent":
        return next((out / f"v{version}").glob("*.md")).read_text(encoding="utf-8")
    if kind == "rule":
        return next((out / f"v{version}").glob("*.md")).read_text(encoding="utf-8")
    if kind in ("mcp", "hook"):
        return (out / f"v{version}" / kind / "manifest.json").read_text(encoding="utf-8")
    if kind == "launch":
        return (out / f"v{version}" / "launch.json").read_text(encoding="utf-8")
    return ""


def _visual_kind(path: Path) -> str:
    if _VIDEO_SUFFIX.search(path.name):
        return "video"
    return "image"


def run_render_video(
    folder: Path,
    *,
    formats: tuple[str, ...],
    size_scale: float,
) -> int:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            _print_error(f"{tool} is not installed; install FFmpeg (https://ffmpeg.org) and try again")
            return 2
    script_path = folder / "script.json"
    if not script_path.is_file():
        _print_error(f"script.json not found in {folder}")
        return 2
    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _print_error(f"script.json in {folder} is not valid JSON")
        return 2
    if not isinstance(data, dict):
        _print_error(f"script.json in {folder} must be a JSON object")
        return 2
    raw_shots = data.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        _print_error("no shots in script.json")
        return 2
    unknown = [name for name in formats if name not in studio.FORMATS]
    if unknown:
        _print_error(f"unknown format {', '.join(unknown)}; use {', '.join(studio.FORMATS)}")
        return 2
    try:
        _scan_folder_paths(folder)
    except HostError as exc:
        _print_error(str(exc))
        return 2
    shots: list[studio.Shot] = []
    for index, raw in enumerate(raw_shots, start=1):
        if not isinstance(raw, dict):
            _print_error(f"shot {index} is not an object")
            return 2
        file_name = raw.get("file")
        if not isinstance(file_name, str) or not file_name.strip():
            _print_error(f"shot {index} needs a file name")
            return 2
        try:
            media = _path_inside(folder, file_name)
        except HostError as exc:
            _print_error(str(exc))
            return 2
        if not media.is_file():
            _print_error(f"shot file not found: {file_name}")
            return 2
        try:
            _require_suffix(file_name, _PICTURE_SUFFIXES | _VIDEO_SUFFIXES, "shot")
        except HostError as exc:
            _print_error(str(exc))
            return 2
        try:
            seconds = max(1, min(20, int(round(float(raw.get("seconds", 4))))))
        except (TypeError, ValueError):
            seconds = 4
        shots.append(studio.Shot(seconds, str(raw.get("visual", "")).strip(), str(raw.get("caption", "")).strip(), str(media)))
    voice_path: str | None = None
    voice_name = data.get("voice_file")
    if isinstance(voice_name, str) and voice_name.strip():
        try:
            voice_path = str(_path_inside(folder, voice_name))
        except HostError as exc:
            _print_error(str(exc))
            return 2
        if not Path(voice_path).is_file():
            _print_error(f"voice file not found: {voice_name}")
            return 2
        try:
            _require_suffix(voice_name, _SOUND_SUFFIXES, "voice")
        except HostError as exc:
            _print_error(str(exc))
            return 2
    music_path: str | None = None
    music_name = data.get("music_file")
    if isinstance(music_name, str) and music_name.strip():
        try:
            music_path = str(_path_inside(folder, music_name))
        except HostError as exc:
            _print_error(str(exc))
            return 2
        if not Path(music_path).is_file():
            _print_error(f"music file not found: {music_name}")
            return 2
        try:
            _require_suffix(music_name, _SOUND_SUFFIXES, "music")
        except HostError as exc:
            _print_error(str(exc))
            return 2
    kinds = {_visual_kind(Path(shot.file or "")) for shot in shots}
    if len(kinds) > 1:
        _print_error("shots mix pictures and video clips; use only pictures or only clips in one video")
        return 2
    visual_kind = kinds.pop()
    production = studio.Production(folder.resolve())
    production.title = str(data.get("title", "")).strip()
    production.voiceover = str(data.get("voiceover", "")).strip()
    production.music_brief = str(data.get("music", "")).strip()
    production.shots = shots
    try:
        studio.assemble(
            folder.resolve(), shots, visual_kind=visual_kind, formats=formats, size_scale=size_scale, captions=True,
            voice_file=voice_path, music_file=music_path, production=production,
        )
    except studio.StudioError as exc:
        _print_error(str(exc))
        return 2
    except OSError as exc:
        _print_error(f"could not render in {folder}: {exc} (a leftover 'work' folder from an earlier run must be removed)")
        return 2
    if production.stopped != "finished":
        _print_error(production.stopped)
        return 2
    production.spent_usd = Decimal(0)
    production.calls = []
    studio._write_record(production, production.title or "host video")
    return 0
