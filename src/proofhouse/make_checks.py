"""Offline checks for generated rules, MCP servers, and command hooks."""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from . import hosts

STEP_TIMEOUT = 10
_ENV_KEYS = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "TEMP", "TMP", "TMPDIR",
             "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LANG", "LC_ALL")
_SAFE_FILE = re.compile(r"[A-Za-z0-9._/-]+")
_DEVICE = re.compile(r"(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?", re.IGNORECASE)
_SAFE_PART = re.compile(r"[A-Za-z0-9_./:=@+,-]+")
_SAFE_COMMAND = re.compile(r"(\./)?[A-Za-z0-9_+][A-Za-z0-9_.+-]*")
_SCRIPT_SUFFIX = re.compile(r"\.[A-Za-z][A-Za-z0-9]*")
_BARE = re.compile(r"[A-Za-z0-9_./:=+-]+")
NOT_ALLOWED = "not checked: add --allow-commands to start it (it runs model-written code with your rights)"
# Written install text never holds this machine's folder layout; the reader fills the placeholder in.
HERE = "<this-folder>"
_HERE_NOTE = (f"Replace {HERE} with the full path of the folder that holds this file, so the path points at the files "
              "you got. Keep the double quotes around it; they let a path with spaces work.")


def parse_json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise ValueError("the model did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("the model did not return a JSON object")
    return value


def safe_name(name: Any) -> bool:
    """A relative file name that stays inside its folder on every OS (no drives, shares, "..", devices, dotted parts).

    No part may start with a dot, so model files cannot reach tool settings or links such as .npmrc or node_modules/.bin.
    The two exceptions are a .well-known folder (app links) and a final file named .gitignore.
    """
    if not (isinstance(name, str) and _SAFE_FILE.fullmatch(name) and not PurePosixPath(name).is_absolute()
            and not PureWindowsPath(name).is_absolute() and ".." not in PurePosixPath(name).parts):
        return False
    parts = PurePosixPath(name).parts
    return not any(_DEVICE.fullmatch(part) or part.endswith(".")
                   or (part.startswith(".") and not (part == (".gitignore" if index == len(parts) - 1 else ".well-known")))
                   for index, part in enumerate(parts))


def write_files(files: Any, folder: Path) -> list[str]:
    if not isinstance(files, dict) or not files or len(files) > 60 or not all(isinstance(v, str) for v in files.values()):
        raise ValueError("files must be a nonempty JSON object of text files (at most 60)")
    if sum(len(value.encode("utf-8")) for value in files.values()) > 3_000_000:
        raise ValueError("generated files exceed 3 MB")
    names: list[str] = []
    for name in files:
        if not safe_name(name):
            raise ValueError(f"unsafe file name: {name!r}")
        names.append(name)
    if len({name.lower() for name in names}) != len(names):
        raise ValueError("two file names differ only in letter case; the second would overwrite the first on Windows and macOS")
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return sorted(names)


@contextmanager
def _throwaway_home(home: Path, phome: Path) -> Iterator[None]:
    names = ("HOME", "USERPROFILE", "PROOFHOUSE_HOME")
    saved = {name: os.environ.get(name) for name in names}
    os.environ.update({"HOME": str(home), "USERPROFILE": str(home), "PROOFHOUSE_HOME": str(phome)})
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def rule(text: str, request: str, folder: Path) -> tuple[str, list[dict[str, Any]]]:
    from .make import _slug

    name = _slug(request)
    content = text
    try:
        value: dict[str, Any] | None = parse_json(text)
    except ValueError:
        value = None
    if value is not None and isinstance(value.get("name"), str) and isinstance(value.get("content"), str):
        name, content = hosts.check_name(value["name"]), value["content"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(content.rstrip("\n") + "\n", encoding="utf-8")
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="rule-check-", dir=folder) as temporary:
        root = Path(temporary)
        project, home, phome = root / "project", root / "home", root / "proofhouse"
        project.mkdir()
        home.mkdir()
        phome.mkdir()
        with _throwaway_home(home, phome):
            for host_id, spec in hosts.all_hosts().items():
                rule_spec = spec.get("rule")
                if not isinstance(rule_spec, dict):
                    continue
                target: hosts.Target | None = None
                before: bytes | None = None
                try:
                    target = hosts.target(host_id, "rule", name, project if "project" in rule_spec else None)
                    if target.format == "md-block":
                        target.path.parent.mkdir(parents=True, exist_ok=True)
                        target.path.write_text("Existing project instructions.\n", encoding="utf-8")
                    before = target.path.read_bytes() if target.path.exists() else None
                    installed = content
                    if target.format == "file" and target.path.suffix == ".mdc" and not content.startswith("---"):
                        installed = f"---\ndescription: {name}\nalwaysApply: true\n---\n{content}"
                    hosts.install(target, installed)
                    hosts.uninstall(target)
                    after = target.path.read_bytes() if target.path.exists() else None
                    ok = after == before
                    detail = "restored exactly" if ok else "file differs after uninstall"
                except (hosts.HostError, OSError, ValueError) as exc:
                    ok, detail = False, str(exc)
                checks.append({"check": f"{host_id} rule install/uninstall", "host": host_id, "ok": ok, "detail": detail,
                               "path": str(target.path.relative_to(root)) if target and target.path.is_relative_to(root) else None})
    return name, checks


def unsafe(command: str, args: list[str]) -> str | None:
    if not _SAFE_COMMAND.fullmatch(command):
        return f"unsafe command {command!r}: give a program name or ./file, with no spaces, folders or shell characters"
    for arg in args:
        if not _SAFE_PART.fullmatch(arg) or ".." in PurePosixPath(arg).parts:
            return f"unsafe argument {arg!r}: use only letters, digits and _ . / : = @ + , - (and no '..')"
        if PurePosixPath(arg).is_absolute() or PureWindowsPath(arg).is_absolute() or PureWindowsPath(arg).drive:
            return f"unsafe argument {arg!r}: name files inside the made folder, not absolute paths"
    return None


def _command(command: str, args: list[str], folder: Path) -> list[str] | None:
    if command.lower() in ("python", "python.exe"):
        executable: str | None = sys.executable
    elif command.startswith("./"):
        candidate = folder / command[2:]
        executable = str(candidate) if candidate.is_file() else None
    else:
        executable = shutil.which(command, path=os.environ.get("PATH"))
    if executable is None:
        return None
    return [executable, *(_local(arg, folder) for arg in args)]


def _environment(folder: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {key: os.environ[key] for key in _ENV_KEYS if key in os.environ}
    env["HOME"] = str(folder)
    env["USERPROFILE"] = str(folder)
    env["TEMP"] = str(folder)
    env["TMP"] = str(folder)
    env["TMPDIR"] = str(folder)
    if folder.drive:
        env["HOMEDRIVE"], env["HOMEPATH"] = folder.drive, str(folder)[len(folder.drive):]
    else:
        env.pop("HOMEDRIVE", None)
        env.pop("HOMEPATH", None)
    env.update(extra or {})
    return env


def _contain(process: subprocess.Popen[bytes]) -> int | None:
    """On Windows, put the process in a job object so everything it starts ends with it."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    process_handle = kernel32.OpenProcess(0x0101, False, process.pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
    joined = bool(process_handle) and bool(kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))) \
        and bool(kernel32.AssignProcessToJobObject(job, process_handle))
    if process_handle:
        kernel32.CloseHandle(process_handle)
    if not joined:
        kernel32.CloseHandle(job)
        return None
    return int(job)


def _kill_tree(process: subprocess.Popen[bytes], job: int | None) -> None:
    if job is not None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.TerminateJobObject(job, 1)
        kernel32.CloseHandle(job)
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=STEP_TIMEOUT, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        process.kill()


def _start(argv: list[str], folder: Path, stderr: Any,
           extra_env: dict[str, str] | None = None, stdout: Any = subprocess.PIPE) -> tuple[subprocess.Popen[bytes], int | None]:
    process = subprocess.Popen(argv, cwd=folder, env=_environment(folder, extra_env), stdin=subprocess.PIPE, stdout=stdout,
                               stderr=stderr, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                               start_new_session=os.name != "nt")
    try:
        return process, _contain(process)
    except BaseException:
        _kill_tree(process, None)
        raise


def build(argv: list[str], folder: Path, timeout: int, extra_env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run a platform-data build step with the same contained process and limited environment (plus extra_env)."""
    process: subprocess.Popen[bytes] | None = None
    job: int | None = None
    # Output goes to a file, not a pipe: a helper left running (such as a Gradle daemon) would hold a pipe open
    # and make a finished build wait for its time limit.
    with tempfile.TemporaryFile() as log:
        try:
            process, job = _start(argv, folder, subprocess.STDOUT, extra_env, stdout=log)
            if process.stdin is not None:
                process.stdin.close()
            code = process.wait(timeout=timeout)
            log.seek(max(0, log.seek(0, os.SEEK_END) - 8000))
            return {"ok": code == 0, "detail": f"exit code {code}", "exit_code": code,
                    "output": log.read().decode("utf-8", errors="replace")[-2000:]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "detail": f"timed out after {timeout} seconds", "exit_code": None, "output": ""}
        except OSError as exc:
            return {"ok": False, "detail": str(exc), "exit_code": None, "output": ""}
        finally:
            if process is not None:
                _kill_tree(process, job)


def mcp(data: dict[str, Any], folder: Path, allow_commands: bool) -> list[dict[str, Any]]:
    command, args = data.get("command"), data.get("args")
    if not isinstance(command, str) or not command or not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        return [{"check": "MCP tools/list", "ok": False, "detail": "command and string args are required"}]
    try:
        hosts.check_name(data.get("name"))
    except hosts.HostError as exc:
        return [{"check": "MCP tools/list", "ok": False, "detail": str(exc)}]
    problem = unsafe(command, args)
    if problem:
        return [{"check": "MCP tools/list", "ok": False, "detail": problem}]
    if not allow_commands:
        return [{"check": "MCP tools/list", "ok": None, "detail": NOT_ALLOWED}]
    argv = _command(command, args, folder)
    if argv is None:
        if command.startswith("./"):
            return [{"check": "MCP tools/list", "ok": False, "detail": f"{command} was not written"}]
        return [{"check": "MCP tools/list", "ok": None, "detail": f"not checked: {command} not found"}]
    try:
        with tempfile.TemporaryFile() as stderr:
            process, job = _start(argv, folder, stderr)
            try:
                responses: queue.Queue[bytes] = queue.Queue()
                def read_lines() -> None:
                    assert process.stdout is not None
                    for line in process.stdout:
                        responses.put(line)
                threading.Thread(target=read_lines, daemon=True).start()
                def exchange(message: dict[str, Any], expected: int | None) -> dict[str, Any]:
                    assert process.stdin is not None
                    process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
                    process.stdin.flush()
                    if expected is None:
                        return {}
                    deadline = time.monotonic() + STEP_TIMEOUT
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError("MCP step timed out")
                        try:
                            line = responses.get(timeout=remaining)
                        except queue.Empty as exc:
                            raise TimeoutError("MCP step timed out") from exc
                        reply = json.loads(line)
                        if isinstance(reply, dict) and reply.get("id") == expected:
                            return reply
                initialized = exchange({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "proofhouse", "version": "1"}}}, 1)
                if "error" in initialized or not isinstance(initialized.get("result"), dict):
                    raise ValueError("initialize failed")
                exchange({"jsonrpc": "2.0", "method": "notifications/initialized"}, None)
                listed = exchange({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, 2)
                if "error" in listed:
                    raise ValueError("tools/list returned an error")
                tools = listed.get("result", {}).get("tools") if isinstance(listed.get("result"), dict) else None
                ok = isinstance(tools, list) and bool(tools) and all(
                    isinstance(tool, dict) and isinstance(tool.get("name"), str) and tool["name"]
                    and isinstance(tool.get("inputSchema"), dict) for tool in tools)
                detail = f"listed {len(tools)} tools" if isinstance(tools, list) else "tools/list did not return tools"
                return [{"check": "MCP tools/list", "ok": ok, "detail": detail + _python_note(command)}]
            finally:
                _kill_tree(process, job)
    except (OSError, ValueError, TimeoutError, BrokenPipeError) as exc:
        return [{"check": "MCP tools/list", "ok": False, "detail": str(exc)}]


def hook(data: dict[str, Any], folder: Path, allow_commands: bool) -> list[dict[str, Any]]:
    event = data.get("event")
    if event not in _known_events():
        return [{"check": "known hook event", "ok": False, "detail": f"unknown event: {event}"}]
    command = data.get("command")
    if not isinstance(command, str) or not command.strip() or not isinstance(data.get("sample_event"), dict):
        return [{"check": "hook execution", "ok": False, "detail": "command and sample_event are required"}]
    parts = command.split()
    problem = unsafe(parts[0], parts[1:])
    if problem:
        return [{"check": "hook execution", "ok": False, "detail": problem}]
    missing = [part for part in parts[1:] if not part.startswith("-") and "://" not in part
               and _SCRIPT_SUFFIX.fullmatch(PurePosixPath(part).suffix) and not (folder / part).is_file()]
    if missing or (parts[0].startswith("./") and not (folder / parts[0][2:]).is_file()):
        return [{"check": "hook execution", "ok": False, "detail": f"names a file that was not written: {(missing or parts)[0]}"}]
    if not allow_commands:
        return [{"check": "hook execution", "ok": None, "detail": NOT_ALLOWED}]
    argv = _command(parts[0], parts[1:], folder)
    if argv is None:
        return [{"check": "hook execution", "ok": None, "detail": f"not checked: {parts[0]} not found"}]
    process: subprocess.Popen[bytes] | None = None
    job: int | None = None
    try:
        process, job = _start(argv, folder, subprocess.PIPE)
        stdout, stderr = process.communicate(json.dumps(data["sample_event"]).encode("utf-8"), timeout=STEP_TIMEOUT)
        code = process.returncode
        ok = code == 0 or (code == 2 and bool(stderr.strip()))
        detail = f"exit code {code}" if ok or code != 2 else "exit code 2 with no reason on stderr (a blocking hook must say why)"
        return [{"check": "hook execution", "ok": ok, "detail": detail + _python_note(parts[0]), "exit_code": code,
                 "stdout": stdout.decode("utf-8", errors="replace")[:2000], "stderr": stderr.decode("utf-8", errors="replace")[:2000]}]
    except subprocess.TimeoutExpired:
        return [{"check": "hook execution", "ok": False, "detail": "timed out after 10 seconds", "exit_code": None,
                 "stdout": "", "stderr": ""}]
    except OSError as exc:
        return [{"check": "hook execution", "ok": False, "detail": str(exc), "exit_code": None,
                 "stdout": "", "stderr": ""}]
    finally:
        if process is not None:
            _kill_tree(process, job)


def _known_events() -> list[str]:
    events_path = Path(__file__).resolve().parent / "data" / "hook_events.json"
    events: list[str] = json.loads(events_path.read_text(encoding="utf-8"))["events"]
    return events


def _python_note(command: str) -> str:
    return " (ran with Proofhouse's own Python; the python you install with may differ)" \
        if command.lower() in ("python", "python.exe") else ""


def _local(part: str, folder: Path) -> str:
    if Path(part).is_absolute() or not (folder / part).is_file():
        return part
    resolved = (folder / part).resolve()
    return str(resolved) if resolved.is_relative_to(folder.resolve()) else part


def _portable(part: str, folder: Path) -> str:
    """A file inside the made folder, written from the folder that holds it (HERE) instead of this machine's path."""
    resolved = Path(_local(part, folder))
    base = folder.resolve()
    if not resolved.is_absolute() or not resolved.is_relative_to(base):
        return part
    return f"{HERE}/{folder.name}/{resolved.relative_to(base).as_posix()}"


def _quoted(part: str, folder: Path) -> str | None:
    """A part as it is pasted into bash, PowerShell or cmd: bare when no shell treats it specially, else in double quotes."""
    value = _portable(part, folder)
    if any(char in value for char in '"$`%!\r\n'):
        return None
    return value if _BARE.fullmatch(value) else f'"{value}"'


def install_line(name: str, command: str, args: list[str], folder: Path) -> str | None:
    if unsafe(command, args):
        return None
    quoted = [_quoted(arg, folder) for arg in args]
    command_part = _quoted(command, folder) if command.startswith("./") else command
    if command_part is None or None in quoted:
        return None
    return f"proofhouse install mcp {name} --command={command_part}" + "".join(f" --arg={arg}" for arg in quoted) + " --into <host>"


def settings_snippet(event: str, matcher: str | None, command: str, folder: Path) -> dict[str, Any] | None:
    parts = command.split()
    if event not in _known_events() or not parts or unsafe(parts[0], parts[1:]):
        return None
    quoted = [_quoted(parts[0], folder) if parts[0].startswith("./") else parts[0], *(_quoted(part, folder) for part in parts[1:])]
    if None in quoted:
        return None
    entry: dict[str, Any] = {"hooks": [{"type": "command", "command": " ".join(str(part) for part in quoted)}]}
    if matcher:
        entry["matcher"] = matcher
    return {"hooks": {event: [entry]}}


def install_text(line: str) -> str:
    """What INSTALL-MCP.txt holds: the install line, and how to fill in the placeholder when it has one."""
    return line + "\n" + (f"\n{_HERE_NOTE}\n" if HERE in line else "")


def snippet_note(snippet: dict[str, Any]) -> str | None:
    """What sits beside settings-snippet.json (JSON cannot carry a note) when its commands have the placeholder."""
    return None if HERE not in json.dumps(snippet) else (
        f"settings-snippet.json goes into your Claude Code settings file under \"hooks\".\n\n{_HERE_NOTE}\n")
