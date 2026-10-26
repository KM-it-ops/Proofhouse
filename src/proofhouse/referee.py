"""Host referee: your agent runs the work loop; Proofhouse runs the check and keeps the record."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .loop import _clean, _secrets

MAX_SUMMARY = 2000
MAX_OUTPUT = 4000

EXIT_OK = 0
EXIT_CONTINUE = 10
EXIT_STOPPED = 11
EXIT_USAGE = 2


class RefereeError(Exception):
    """A referee command cannot run; the message says why."""

_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|DATABASE_URL|CONNECTION_STRING|AUTH", re.IGNORECASE)
# The check sees only these variables, so a secret under any name (GH_PAT, POSTGRES_URL, ...) stays out.
_CHECK_ENV_KEYS = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "TEMP", "TMP", "TMPDIR",
                   "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
                   "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "COMMONPROGRAMFILES", "NUMBER_OF_PROCESSORS",
                   "PROCESSOR_ARCHITECTURE", "OS", "USERNAME", "USER", "LOGNAME", "SHELL", "TERM", "LANG", "LC_ALL",
                   "LC_CTYPE", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")


def _secret_values() -> list[str]:
    named = [value for name, value in os.environ.items() if _SECRET_NAME.search(name) and len(value) >= 6]
    return sorted({*_secrets(), *named}, key=len, reverse=True)


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()


def _run_check(command: str, cwd: Path, timeout: int) -> dict[str, Any]:
    wanted = {name.upper() for name in _CHECK_ENV_KEYS}
    env = {k: v for k, v in os.environ.items() if k.upper() in wanted and not _SECRET_NAME.search(k)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.Popen(command, shell=True, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace", start_new_session=os.name != "nt")
    except OSError as exc:
        return {"exit": None, "output": f"could not start: {exc}"}
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return {"exit": None, "output": f"stopped after {timeout} seconds"}
    return {"exit": proc.returncode, "output": out or ""}


def _fingerprint(check: str, workdir: str, timeout: int) -> str:
    return hashlib.sha256(json.dumps([check, workdir, timeout]).encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _atomic_write(path: Path, content: str) -> None:
    if path.is_symlink():
        raise RefereeError(f"symbolic link not allowed: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".proofhouse-tmp")
    temporary = Path(name)
    try:
        os.close(handle)
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise RefereeError(f"cannot write {path}: {exc}") from exc


def _refuse_symlink(path: Path) -> None:
    if path.is_symlink():
        raise RefereeError(f"symbolic link not allowed: {path}")


def _check_paths(workdir: Path, out: Path) -> None:
    work_root, out_root = workdir.resolve(), out.resolve()
    if not work_root.is_dir():
        raise RefereeError(f"{workdir} is not a folder")
    if out_root == work_root or out_root.is_relative_to(work_root) or work_root.is_relative_to(out_root):
        raise RefereeError("--out must be a separate folder that neither holds nor sits inside the work folder")
    if out.exists() and not out.is_dir():
        raise RefereeError(f"--out is not a folder: {out}")
    if out.is_dir() and any(out.iterdir()):
        raise RefereeError(f"--out folder is not empty: {out} (pick a new or empty folder)")


def _read_loop(out: Path) -> dict[str, Any]:
    path = out / "loop.json"
    if not path.is_file():
        raise RefereeError(f"no referee record in {out} (run `proofhouse referee start` first)")
    _refuse_symlink(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RefereeError(f"loop.json in {out} is not readable JSON") from exc
    if not isinstance(data, dict):
        raise RefereeError(f"loop.json in {out} must be a JSON object")
    return data


def _write_loop(out: Path, data: dict[str, Any]) -> None:
    _atomic_write(out / "loop.json", json.dumps(data, indent=2, sort_keys=True) + "\n")


def _rounds_path(out: Path) -> Path:
    path = out / "rounds.jsonl"
    _refuse_symlink(path)
    return path


def _count_rounds(out: Path) -> int:
    path = _rounds_path(out)
    if not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return 0
    return len([line for line in text.splitlines() if line.strip()])


def _last_round(out: Path) -> dict[str, Any] | None:
    path = _rounds_path(out)
    if not path.is_file():
        return None
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    try:
        row = json.loads(lines[-1])
    except ValueError as exc:
        raise RefereeError("the last line of rounds.jsonl is not readable JSON") from exc
    return row if isinstance(row, dict) else None


def _elapsed_seconds(loop: dict[str, Any], now: datetime) -> float:
    started = datetime.fromisoformat(loop["started_at"])
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return (now - started).total_seconds()


def start_referee(
    goal: str,
    *,
    check: str,
    workdir: Path,
    out_dir: Path,
    max_rounds: int,
    max_seconds: float | None,
    agent: str,
    command_timeout: int,
    allow_commands: bool,
) -> Path:
    if not allow_commands:
        raise RefereeError("a check command needs --allow-commands")
    if not check.strip():
        raise RefereeError("--check is required")
    if max_rounds < 1:
        raise RefereeError("--rounds must be at least 1")
    if command_timeout < 1:
        raise RefereeError("--command-timeout must be at least 1 second")
    secrets = _secret_values()
    goal, check, agent = (_clean(text, secrets, 2000) for text in (goal, check, agent))
    workdir = workdir.resolve()
    out_dir = out_dir.resolve()
    _check_paths(workdir, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "proofhouse_version": __version__,
        "goal": goal,
        "check": check,
        "workdir": str(workdir),
        "rounds_limit": max_rounds,
        "seconds_limit": max_seconds,
        "command_timeout": command_timeout,
        "check_fingerprint": _fingerprint(check, str(workdir), command_timeout),
        "agent": agent,
        "started_at": _utc_now().isoformat(timespec="seconds"),
        "mode": "host",
        "status": "running",
    }
    _write_loop(out_dir, record)
    _rounds_path(out_dir).write_text("", encoding="utf-8")
    return out_dir


def run_round(
    out: Path,
    summary: str,
    *,
    agent: str,
    allow_commands: bool,
    command_timeout: int | None = None,
    now: Callable[[], datetime] | None = None,
) -> int:
    if not allow_commands:
        raise RefereeError("a check command needs --allow-commands")
    out = out.resolve()
    loop = _read_loop(out)
    if loop.get("status") != "running":
        raise RefereeError(f"referee is not running (status is {loop.get('status')!r})")
    try:
        stored_timeout = int(loop.get("command_timeout", 300))
        workdir = Path(loop["workdir"])
        check = str(loop["check"])
        limit_rounds = int(loop["rounds_limit"])
        limit_seconds = loop.get("seconds_limit")
        limit_seconds = None if limit_seconds is None else float(limit_seconds)
        elapsed = _elapsed_seconds(loop, (now or _utc_now)())
    except (KeyError, TypeError, ValueError) as exc:
        raise RefereeError("loop.json is damaged (a field is missing or wrong); start a new referee") from exc
    if loop.get("check_fingerprint") != _fingerprint(check, str(workdir), stored_timeout):
        raise RefereeError("loop.json was changed after start (check, folder or timeout); start a new referee")
    work_root = workdir.resolve()
    if not work_root.is_dir() or out == work_root or out.is_relative_to(work_root) or work_root.is_relative_to(out):
        raise RefereeError("the work folder is missing or overlaps the record folder; start a new referee")
    timeout = command_timeout if command_timeout is not None else stored_timeout
    if timeout < 1:
        raise RefereeError("--command-timeout must be at least 1 second")
    summary = _clean(summary[:MAX_SUMMARY], _secret_values(), MAX_SUMMARY)
    secrets = _secret_values()
    started = time.monotonic()
    outcome = _run_check(check, workdir, timeout)
    output = _clean(outcome["output"], secrets, MAX_OUTPUT)
    if len(output) > MAX_OUTPUT:
        output = "…" + output[-(MAX_OUTPUT - 1) :]
    seconds = time.monotonic() - started
    round_no = _count_rounds(out) + 1
    row = {
        "round": round_no,
        "at": _utc_now().isoformat(timespec="seconds"),
        "summary": summary,
        "agent": agent,
        "check_exit": outcome["exit"],
        "check_passed": outcome["exit"] == 0,
        "check_output": output,
        "seconds": round(seconds, 3),
    }
    path = _rounds_path(out)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")

    if outcome["exit"] == 0:
        loop["status"] = "done"
        _write_loop(out, loop)
        print("passed: check passed")
        return EXIT_OK
    if round_no >= limit_rounds:
        loop["status"] = "stopped"
        _write_loop(out, loop)
        print("rounds: round limit reached")
        return EXIT_STOPPED
    if limit_seconds is not None and elapsed > limit_seconds:
        loop["status"] = "stopped"
        _write_loop(out, loop)
        print("time: time limit reached")
        return EXIT_STOPPED
    print("continue: keep going")
    return EXIT_CONTINUE


def run_status(out: Path, *, as_json: bool = False) -> None:
    out = out.resolve()
    loop = _read_loop(out)
    last = _last_round(out)
    used = _count_rounds(out)
    payload = {
        "goal": loop.get("goal"),
        "rounds_used": used,
        "rounds_limit": loop.get("rounds_limit"),
        "status": loop.get("status"),
        "last_check_passed": last.get("check_passed") if last else None,
        "last_check_exit": last.get("check_exit") if last else None,
    }
    if as_json:
        print(json.dumps(payload, sort_keys=True))
        return
    print(f"goal: {_clean(str(payload['goal']), [], 500).encode('unicode_escape').decode('ascii')}")
    print(f"rounds: {used} / {payload['rounds_limit']}")
    if last is None:
        print("last check: (none yet)")
    elif last.get("check_passed"):
        print("last check: passed")
    else:
        print(f"last check: failed (exit {last.get('check_exit')})")
    print(f"status: {payload['status']}")
