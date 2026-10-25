"""PreToolUse hook: block destructive Bash commands (git-guard). Stdlib only."""

from __future__ import annotations

import json
import re
import shlex
import sys

EXIT_ALLOW = 0
EXIT_BLOCK = 2

_DB_SHELLS = ("psql", "sqlite3", "mysql", "mariadb")
_DROP_RE = re.compile(r"\bdrop\s+(?:database|table)\b", re.IGNORECASE)
_GIT_GLOBAL_WITH_VALUE = frozenset(
    {"-C", "-c", "--exec-path", "--git-dir", "--work-tree", "--namespace"}
)
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
    pipeline = split_on_operators(command, {"|"})
    if pipeline_has_sql_drop(pipeline):
        return "blocked: DROP DATABASE / DROP TABLE via database shell"

    flags = {"push": False, "reset_hard": False, "clean_fd": False}

    for stage in pipeline:
        for segment in split_on_operators(stage, {"\n", ";", "&&", "||", "&"}):
            seg = segment.strip()
            if not seg:
                continue
            reason = inspect_segment(seg, flags)
            if reason:
                return reason

    if flags["push"] and (flags["reset_hard"] or flags["clean_fd"]):
        return "blocked: destructive git cleanup chained with push"
    return None


def inspect_segment(segment: str, flags: dict[str, bool]) -> str | None:
    peeled = peel_outer_group(segment)
    if peeled is not None:
        return inspect_command(peeled)

    for payload in extract_wrapper_payloads(segment):
        reason = inspect_command(payload)
        if reason:
            return reason

    cmd = strip_wrappers(segment)
    if not cmd:
        return None

    if is_force_push(cmd):
        return "blocked: git force-push is not allowed (use --force-with-lease if you must overwrite remote)"

    if is_dangerous_rm(cmd):
        return "blocked: recursive delete on a system-wide or home path"

    tokens = safe_shlex(cmd)
    if tokens and tokens[0] == "git":
        sub, args = git_subcommand(tokens)
        if sub == "push":
            flags["push"] = True
        elif sub == "reset" and "--hard" in args:
            flags["reset_hard"] = True
        elif sub == "clean" and has_clean_fd_flags(args):
            flags["clean_fd"] = True

    return None


def split_on_operators(text: str, operators: set[str]) -> list[str]:
    """Split text on operators outside quotes. Multi-char ops (&&, ||) checked first."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(text)
    in_single = False
    in_double = False

    def flush() -> None:
        parts.append("".join(buf))
        buf.clear()

    while i < n:
        if in_single:
            buf.append(text[i])
            if text[i] == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            buf.append(text[i])
            if text[i] == '"' and (i == 0 or text[i - 1] != "\\"):
                in_double = False
            i += 1
            continue
        if text[i] == "'":
            in_single = True
            buf.append(text[i])
            i += 1
            continue
        if text[i] == '"':
            in_double = True
            buf.append(text[i])
            i += 1
            continue

        matched = False
        for op in sorted(operators, key=len, reverse=True):
            if text[i : i + len(op)] == op:
                flush()
                i += len(op)
                matched = True
                break
        if matched:
            continue

        buf.append(text[i])
        i += 1

    flush()
    if not parts:
        return [text]
    return parts


def peel_outer_group(segment: str) -> str | None:
    s = segment.strip()
    if len(s) < 2:
        return None
    open_ch, close_ch = s[0], s[-1]
    if open_ch not in ("(", "{") or close_ch != (")" if open_ch == "(" else "}"):
        return None
    inner = s[1:-1].strip()
    if open_ch == "{" and inner.endswith(";"):
        inner = inner[:-1].strip()
    return inner if inner else None


def extract_wrapper_payloads(segment: str) -> list[str]:
    """Return quoted payloads from bash/sh -c, eval, etc. for recursive inspection."""
    tokens = safe_shlex(segment.strip())
    if not tokens:
        return []

    payloads: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("bash", "sh", "zsh") and i + 2 < len(tokens) and tokens[i + 1] == "-c":
            payloads.append(tokens[i + 2])
            return payloads
        if tok == "eval" and i + 1 < len(tokens):
            payloads.append(tokens[i + 1])
            return payloads
        if tok == "xargs":
            rest = xargs_command_tokens(tokens[i + 1 :])
            if rest:
                payloads.append(" ".join(shlex.quote(t) for t in rest))
            return payloads
        i += 1
    return payloads


def xargs_command_tokens(tokens: list[str]) -> list[str]:
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "--":
            return tokens[i + 1 :]
        if t.startswith("-") and t not in ("-I", "-i", "-n", "-P", "-L", "-s"):
            if "=" in t:
                i += 1
                continue
            if t in ("-I", "-i", "-n", "-P", "-L", "-s") and i + 1 < len(tokens):
                i += 2
                continue
            i += 1
            continue
        if t.startswith("-I") and len(t) > 2:
            i += 1
            continue
        if t in ("-I", "-i", "-n", "-P", "-L", "-s") and i + 1 < len(tokens):
            i += 2
            continue
        return tokens[i:]
    return []


def strip_wrappers(segment: str) -> str:
    seg = segment.strip()
    while seg:
        tokens = safe_shlex(seg)
        if not tokens:
            return seg

        if tokens[0] == "sudo":
            seg = seg[seg.find(tokens[1]) if len(tokens) > 1 else len(seg) :].strip()
            if not seg and len(tokens) > 1:
                seg = " ".join(shlex.quote(t) for t in tokens[1:])
            continue

        if tokens[0] in ("time", "nohup", "command"):
            seg = " ".join(shlex.quote(t) for t in tokens[1:]).strip()
            continue

        if tokens[0] == "env":
            j = 1
            while j < len(tokens):
                t = tokens[j]
                if t == "-i" or t == "--":
                    j += 1
                    continue
                if "=" in t or t.startswith("-"):
                    j += 1
                    continue
                break
            seg = " ".join(shlex.quote(t) for t in tokens[j:]).strip()
            continue

        if tokens[0] in ("bash", "sh", "zsh") and len(tokens) >= 3 and tokens[1] == "-c":
            return ""

        if tokens[0] == "eval":
            return ""

        if tokens[0] == "xargs":
            rest = xargs_command_tokens(tokens[1:])
            if rest:
                seg = " ".join(shlex.quote(t) for t in rest).strip()
                continue
            return ""

        # VAR=value prefix (simple assignment before command)
        m = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*=(?:[^\s]+|\"[^\"]*\"|'[^']*')\s+)+",
            seg,
        )
        if m:
            seg = seg[m.end() :].strip()
            continue

        break
    return seg


def pipeline_has_sql_drop(stages: list[str]) -> bool:
    has_shell = False
    has_drop = False
    for stage in stages:
        low = stage.lower()
        tokens = safe_shlex(stage.strip())
        if tokens and tokens[0] in _DB_SHELLS:
            has_shell = True
        elif any(shell in low for shell in _DB_SHELLS):
            has_shell = True
        if _DROP_RE.search(stage):
            has_drop = True
    return has_shell and has_drop


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
        i = _skip_git_globals(tokens, i)
        if i >= len(tokens):
            return None, []
        return tokens[i], tokens[i + 1 :]
    return None, []


def _skip_git_globals(tokens: list[str], i: int) -> int:
    while i < len(tokens):
        t = tokens[i]
        if t in _GIT_GLOBAL_WITH_VALUE:
            i += 2
            continue
        if t.startswith("-") and "=" in t:
            i += 1
            continue
        if t.startswith("-") and t != "--":
            i += 1
            continue
        if t == "--":
            break
        break
    return i


def is_force_push(segment: str) -> bool:
    tokens = safe_shlex(segment)
    sub, args = git_subcommand(tokens)
    if sub != "push":
        return False
    return _push_args_force(args)


def _push_args_force(args: list[str]) -> bool:
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            if arg.startswith("--force-with-lease") or arg.startswith("--force-if-includes"):
                i += 1
                continue
            if arg == "--force" or arg.startswith("--force="):
                return True
            i += 1
            continue
        if arg.startswith("-") and len(arg) > 1:
            if "f" in arg[1:]:
                return True
            i += 1
            continue
        if arg.startswith("+") and not arg.startswith("++"):
            return True
        i += 1
    for arg in args:
        if not arg.startswith("-") and arg.startswith("+") and not arg.startswith("++"):
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
        if tok == "--":
            paths.extend(tokens[tokens.index(tok) + 1 :])
            break
        if tok.startswith("-") and tok != "--":
            body = tok[1:]
            if body and body[0] == "-":
                body = body[1:]
            if "r" in body:
                recursive = True
            if "f" in body:
                force = True
        else:
            paths.append(tok)
    if not (recursive and force):
        return False
    for path in paths:
        if _normalize_rm_target(path) in ("/", "~home"):
            return True
    return False


def _normalize_rm_target(path: str) -> str:
    p = path.strip().strip('"').strip("'")
    if p in ("~", "$HOME", "${HOME}"):
        return "~home"
    p = re.sub(r"\$\{HOME\}", "", p)
    p = p.replace("$HOME", "")
    if p == "" or p == "~":
        return "~home"
    if p.startswith("~/"):
        return "~home"
    while p.endswith("/") or p.endswith("*"):
        p = p[:-1]
    if p == "":
        return "/"
    if p in ("/", ".", ".."):
        return "/"
    return p


def has_clean_fd_flags(args: list[str]) -> bool:
    for arg in args:
        if arg.startswith("-") and "f" in arg and "d" in arg:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
