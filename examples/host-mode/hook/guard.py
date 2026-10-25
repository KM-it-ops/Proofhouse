"""PreToolUse hook: block destructive Bash commands (git-guard). Stdlib only."""

from __future__ import annotations

import json
import re
import shlex
import sys

EXIT_ALLOW = 0
EXIT_BLOCK = 2


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return EXIT_ALLOW
        event = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        return EXIT_ALLOW

    if not isinstance(event, dict):
        return EXIT_ALLOW
    if event.get("tool_name") != "Bash":
        return EXIT_ALLOW

    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return EXIT_ALLOW
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return EXIT_ALLOW

    reason = inspect_command(command)
    if reason:
        print(reason, file=sys.stderr)
        return EXIT_BLOCK
    return EXIT_ALLOW


def inspect_command(command: str) -> str | None:
    segments = split_segments(command)
    has_push = False
    has_reset_hard = False
    has_clean_fd = False

    for segment in segments:
        seg = strip_leading_sudo(segment.strip())
        if not seg:
            continue

        if is_force_push(seg):
            return "blocked: git force-push is not allowed (use --force-with-lease if you must overwrite remote)"

        if is_dangerous_rm(seg):
            return "blocked: recursive delete on a system-wide or home path"

        if is_db_drop(seg):
            return "blocked: DROP DATABASE / DROP TABLE via database shell"

        tokens = safe_shlex(seg)
        if tokens and tokens[0] == "git":
            sub, args = git_subcommand(tokens)
            if sub == "push":
                has_push = True
            elif sub == "reset" and "--hard" in args:
                has_reset_hard = True
            elif sub == "clean" and has_clean_fd_flags(args):
                has_clean_fd = True

    if has_push and (has_reset_hard or has_clean_fd):
        return "blocked: destructive git cleanup chained with push"
    return None


def split_segments(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    in_single = False
    in_double = False
    n = len(command)

    def flush() -> None:
        piece = "".join(buf).strip()
        if piece:
            parts.append(piece)
        buf.clear()

    while i < n:
        ch = command[i]
        if in_single:
            buf.append(ch)
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            buf.append(ch)
            if ch == '"' and (i == 0 or command[i - 1] != "\\"):
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            buf.append(ch)
            i += 1
            continue
        if command[i : i + 2] == "&&":
            flush()
            i += 2
            continue
        if command[i : i + 2] == "||":
            flush()
            i += 2
            continue
        if ch in ";|":
            flush()
            i += 1
            continue
        buf.append(ch)
        i += 1
    flush()
    return parts if parts else [command.strip()]


def strip_leading_sudo(segment: str) -> str:
    seg = segment.strip()
    while True:
        if seg.startswith("sudo "):
            seg = seg[5:].lstrip()
            continue
        m = re.match(r"^[A-Za-z_][A-Za-z0-9_]*=(?:[^\s]+|\"[^\"]*\"|'[^']*')\s+", seg)
        if m:
            seg = seg[m.end() :].lstrip()
            if seg.startswith("sudo "):
                continue
        break
    return seg


def safe_shlex(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def git_subcommand(tokens: list[str]) -> tuple[str | None, list[str]]:
    i = 0
    while i < len(tokens):
        if tokens[i] != "git":
            i += 1
            continue
        i += 1
        while i < len(tokens) and tokens[i].startswith("-") and tokens[i] != "--":
            i += 1
        if i >= len(tokens):
            return None, []
        sub = tokens[i]
        return sub, tokens[i + 1 :]
    return None, []


def is_force_push(segment: str) -> bool:
    tokens = safe_shlex(segment)
    sub, args = git_subcommand(tokens)
    if sub != "push":
        return False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--force-with-lease":
            i += 1
            continue
        if arg in ("--force", "-f") or arg.startswith("--force="):
            return True
        if arg.startswith("+") and not arg.startswith("++"):
            return True
        i += 1
    for arg in args:
        if not arg.startswith("-") and arg.startswith("+"):
            return True
    return False


def is_dangerous_rm(segment: str) -> bool:
    tokens = safe_shlex(segment)
    if not tokens or tokens[0] != "rm":
        return False
    recursive = False
    force = False
    paths: list[str] = []
    for tok in tokens[1:]:
        if tok.startswith("-") and tok != "--":
            if "r" in tok:
                recursive = True
            if "f" in tok:
                force = True
        elif tok == "--":
            paths.extend(tokens[tokens.index(tok) + 1 :])
            break
        else:
            paths.append(tok)
    if not (recursive and force):
        return False
    for path in paths:
        if path in ("/", "~", "$HOME", "*"):
            return True
        if path in ("/.", "/.."):
            return True
    return False


def has_clean_fd_flags(args: list[str]) -> bool:
    for arg in args:
        if arg.startswith("-") and "f" in arg and "d" in arg:
            return True
    return False


def is_db_drop(segment: str) -> bool:
    lowered = segment.lower()
    if not any(shell in lowered for shell in ("psql", "sqlite3", "mysql")):
        return False
    # SQL for -c / -e lives inside quotes; do not strip those away.
    return "drop database" in lowered or "drop table" in lowered


if __name__ == "__main__":
    raise SystemExit(main())
