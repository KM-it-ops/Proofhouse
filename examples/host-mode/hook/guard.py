"""PreToolUse hook: block destructive Bash commands (git-guard). Stdlib only."""

from __future__ import annotations

import json
import re
import shlex
import sys

EXIT_ALLOW = 0
EXIT_BLOCK = 2

_SQL_REASON = "blocked: DROP DATABASE / DROP TABLE via database shell"
_DB_SHELLS = ("psql", "sqlite3", "mysql", "mariadb")
_DROP_RE = re.compile(r"\bdrop\s+(?:database|table)\b", re.IGNORECASE)
_GIT_GLOBAL_WITH_VALUE = frozenset(
    {"-C", "-c", "--exec-path", "--git-dir", "--work-tree", "--namespace"}
)
_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
_C_FLAG_RE = re.compile(r"-[A-Za-z]*c[A-Za-z]*")
_SHELL_OPTS_WITH_VALUE = frozenset({"-o", "+o", "-O", "+O", "--rcfile", "--init-file"})
_SUDO_SHORT_WITH_VALUE = frozenset("ughpCDRTU")
_SUDO_LONG_WITH_VALUE = frozenset(
    {
        "--user", "--group", "--host", "--prompt", "--close-from", "--chdir",
        "--chroot", "--role", "--type", "--other-user", "--command-timeout",
    }
)
_ENV_WITH_VALUE = frozenset({"-u", "--unset", "-C", "--chdir"})
_SHELL_KEYWORDS = frozenset({"then", "do", "else", "elif", "if", "while", "until", "!", "{"})
# wrapper command -> (options that take a value, positional arguments before the real command)
_WRAPPERS = {
    "time": (frozenset(), 0),
    "nohup": (frozenset(), 0),
    "command": (frozenset(), 0),
    "setsid": (frozenset(), 0),
    "exec": (frozenset({"-a"}), 0),
    "nice": (frozenset({"-n", "--adjustment"}), 0),
    "stdbuf": (frozenset({"-i", "-o", "-e", "--input", "--output", "--error"}), 0),
    "timeout": (frozenset({"-k", "-s", "--kill-after", "--signal"}), 1),
}
_HOME_DIRS = ("~", "$HOME", "${HOME}", "$USERPROFILE", "${USERPROFILE}")
_HEREDOC_RE = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([A-Za-z_][A-Za-z0-9_]*))"
)
_CONTINUATION_RE = re.compile(r"\\\r?\n")
# parentheses separate commands too: (cd x && git push -f) and $(git push -f)
_SEGMENT_OPS = {"\n", ";", "&&", "||", "&", "|", "(", ")"}
_CHUNK_OPS = _SEGMENT_OPS - {"|"}


def _base(token: str) -> str:
    """Command name without its directory or .exe: /usr/bin/git, Git.exe -> git."""
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def _shell_c_payload(tokens: list[str], i: int) -> str | None:
    """Payload of `bash -c '...'` (also -lc, -o pipefail -c, extra flags) when tokens[i] is a shell."""
    if _base(tokens[i]) not in _SHELLS:
        return None
    j = i + 1
    while j < len(tokens) and tokens[j].startswith(("-", "+")):
        t = tokens[j]
        if _C_FLAG_RE.fullmatch(t):
            return tokens[j + 1] if j + 1 < len(tokens) else None
        takes_value = t in _SHELL_OPTS_WITH_VALUE or (
            t.startswith("-") and not t.startswith("--") and t[-1] in "oO"
        )
        j += 2 if takes_value else 1
    return None


def _requote(tokens: list[str]) -> str:
    return " ".join(shlex.quote(t) for t in tokens).strip()


def main() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        if not raw.strip():
            return EXIT_ALLOW
        event = json.loads(raw)
    except (ValueError, TypeError, RecursionError):
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

    try:
        reason = inspect_command(command)
    except RecursionError:
        reason = "blocked: command is nested too deeply to inspect"
    if reason:
        print(reason, file=sys.stderr)
        return EXIT_BLOCK
    return EXIT_ALLOW


def inspect_command(command: str) -> str | None:
    command = _CONTINUATION_RE.sub("", command)
    code, heredocs = split_heredocs(command)

    # A here-document body is data, unless the shell runs it or a database shell reads it.
    for header, body, quoted in heredocs:
        if _runs_command(header, _DB_SHELLS) and _DROP_RE.search(body):
            return _SQL_REASON
        if _runs_command(header, _SHELLS):
            payloads = [body]
        elif quoted:
            payloads = []
        else:
            payloads = command_substitutions(body)
        for payload in payloads:
            reason = inspect_command(payload)
            if reason:
                return reason

    for payload in command_substitutions(code):
        reason = inspect_command(payload)
        if reason:
            return reason

    for chunk in split_on_operators(code, _CHUNK_OPS):
        if segment_has_sql_drop(chunk):
            return _SQL_REASON

    flags = {"push": False, "reset_hard": False, "clean_fd": False}
    for seg in split_on_operators(code, _SEGMENT_OPS):
        if not seg.strip():
            continue
        reason = inspect_segment(seg.strip(), flags)
        if reason:
            return reason

    if flags["push"] and (flags["reset_hard"] or flags["clean_fd"]):
        return "blocked: destructive git cleanup chained with push"
    return None


def inspect_segment(segment: str, flags: dict[str, bool]) -> str | None:
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
    if tokens and _base(tokens[0]) == "git":
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
    ops = sorted(operators, key=len, reverse=True)
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(text)
    in_single = False
    in_double = False

    while i < n:
        ch = text[i]
        if in_single:
            buf.append(ch)
            in_single = ch != "'"
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(text[i : i + 2])
            i += 2
            continue
        if in_double:
            buf.append(ch)
            in_double = ch != '"'
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

        op = next((o for o in ops if text.startswith(o, i)), None)
        if op:
            parts.append("".join(buf))
            buf.clear()
            i += len(op)
            continue

        buf.append(ch)
        i += 1

    parts.append("".join(buf))
    return parts


def split_heredocs(command: str) -> tuple[str, list[tuple[str, str, bool]]]:
    """Take here-document bodies out of the command.

    Returns the command without the bodies (so their lines are not mistaken for
    commands) and a (header line, body, quoted delimiter) tuple for each one. A body
    with no closing delimiter stays in the command as well, so nothing is hidden.
    """
    lines = command.split("\n")
    kept: list[str] = []
    docs: list[tuple[str, str, bool]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        i += 1
        for m in _HEREDOC_RE.finditer(line):
            strip_tabs = bool(m.group(1))
            delim = m.group(2) or m.group(3) or m.group(5)
            if not delim:
                continue
            quoted = m.group(5) is None or bool(m.group(4))
            end = i
            while end < len(lines):
                cand = lines[end].rstrip("\r")
                if (cand.lstrip("\t") if strip_tabs else cand) == delim:
                    break
                end += 1
            else:
                docs.append((line, "\n".join(lines[i:]), True))
                continue
            docs.append((line, "\n".join(lines[i:end]), quoted))
            i = end + 1
    return "\n".join(kept), docs


def command_substitutions(text: str) -> list[str]:
    """Bodies of $(...) and `...` the shell would run: none inside single quotes.

    Nested ones are found when the outer body is inspected in turn.
    """
    found: list[str] = []
    i = 0
    n = len(text)
    in_single = False
    in_double = False
    while i < n:
        ch = text[i]
        if in_single:
            in_single = ch != "'"
            i += 1
        elif ch == "\\":
            i += 2
        elif ch == "'" and not in_double:
            in_single = True
            i += 1
        elif ch == '"':
            in_double = not in_double
            i += 1
        elif ch == "`":
            end = text.find("`", i + 1)
            if end < 0:
                break
            found.append(text[i + 1 : end])
            i = end + 1
        elif text.startswith("$((", i):
            i += 3
        elif text.startswith("$(", i):
            depth = 1
            j = i + 2
            while j < n and depth:
                depth += (text[j] == "(") - (text[j] == ")")
                j += 1
            found.append(text[i + 2 : j - 1 if depth == 0 else j])
            i = j
        else:
            i += 1
    return found


def _runs_command(text: str, names: frozenset[str] | tuple[str, ...]) -> bool:
    """True when one of `names` is the command being run in some part of `text`."""
    for stage in split_on_operators(text, _SEGMENT_OPS):
        tokens = safe_shlex(strip_wrappers(stage.strip()))
        if tokens and _base(tokens[0]) in names:
            return True
    return False


def extract_wrapper_payloads(segment: str) -> list[str]:
    """Return quoted payloads from bash/sh -c, eval, etc. for recursive inspection."""
    tokens = safe_shlex(segment.strip())
    if not tokens:
        return []

    payloads: list[str] = []
    i = 0
    while i < len(tokens):
        tok = _base(tokens[i])
        shell_payload = _shell_c_payload(tokens, i)
        if shell_payload is not None:
            payloads.append(shell_payload)
            return payloads
        if tok == "eval" and i + 1 < len(tokens):
            payloads.append(" ".join(tokens[i + 1 :]))
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


def _skip_options(tokens: list[str], value_opts: frozenset[str], positionals: int = 0) -> list[str]:
    """Tokens left after a wrapper's own options (and its leading positional arguments)."""
    j = 1
    while j < len(tokens) and tokens[j].startswith("-") and tokens[j] != "--":
        j += 2 if tokens[j] in value_opts else 1
    if j < len(tokens) and tokens[j] == "--":
        j += 1
    return tokens[j + positionals :]


def _sudo_command(tokens: list[str]) -> list[str]:
    j = 1
    while j < len(tokens) and tokens[j].startswith("-") and tokens[j] != "--":
        t = tokens[j]
        takes_value = t in _SUDO_LONG_WITH_VALUE or (
            not t.startswith("--") and t[-1] in _SUDO_SHORT_WITH_VALUE
        )
        j += 2 if takes_value else 1
    if j < len(tokens) and tokens[j] == "--":
        j += 1
    return tokens[j:]


def strip_wrappers(segment: str) -> str:
    seg = segment.strip()
    while seg:
        tokens = safe_shlex(seg)
        if not tokens:
            return seg

        head = _base(tokens[0])

        if head == "sudo":
            seg = _requote(_sudo_command(tokens))
            continue

        if head in _WRAPPERS:
            value_opts, positionals = _WRAPPERS[head]
            seg = _requote(_skip_options(tokens, value_opts, positionals))
            continue

        if head in _SHELL_KEYWORDS:
            seg = _requote(tokens[1:])
            continue

        if head == "env":
            j = 1
            while j < len(tokens):
                t = tokens[j]
                if t in _ENV_WITH_VALUE:
                    j += 2
                    continue
                if t == "-i" or t == "--" or "=" in t or t.startswith("-"):
                    j += 1
                    continue
                break
            seg = _requote(tokens[j:])
            continue

        if _shell_c_payload(tokens, 0) is not None or head == "eval":
            return ""

        if head == "xargs":
            rest = xargs_command_tokens(tokens[1:])
            if rest:
                seg = " ".join(shlex.quote(t) for t in rest).strip()
                continue
            return ""

        # VAR=value prefix (simple assignment before command; the value may be quoted)
        m = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|[^\s\"'])*\s+)+",
            seg,
        )
        if m:
            seg = seg[m.end() :].strip()
            continue

        break
    return seg


def segment_has_sql_drop(chunk: str) -> bool:
    """True when a database shell runs in this chunk and a DROP statement is fed to it.

    The shell must be in command position (so a commit message that merely mentions
    psql is fine). Only the stages up to the last database shell can feed it, so
    `sqlite3 db .dump | grep "DROP TABLE"` is fine.
    """
    stages = split_on_operators(chunk, {"|"})
    last_shell = -1
    for idx, stage in enumerate(stages):
        tokens = safe_shlex(strip_wrappers(stage.strip()))
        if tokens and _base(tokens[0]) in _DB_SHELLS:
            last_shell = idx
    if last_shell < 0:
        return False
    return bool(_DROP_RE.search("|".join(stages[: last_shell + 1])))


def safe_shlex(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def git_subcommand(tokens: list[str]) -> tuple[str | None, list[str]]:
    if not tokens or _base(tokens[0]) != "git":
        return None, []
    i = _skip_git_globals(tokens, 1)
    if i >= len(tokens):
        return None, []
    return tokens[i], tokens[i + 1 :]


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
    if not tokens or _base(tokens[0]) != "rm":
        return False
    recursive = False
    paths: list[str] = []
    args = tokens[1:]
    for idx, tok in enumerate(args):
        if tok == "--":
            paths.extend(args[idx + 1 :])
            break
        if tok.startswith("--"):
            recursive = recursive or tok == "--recursive"
        elif tok.startswith("-") and len(tok) > 1:
            recursive = recursive or "r" in tok[1:] or "R" in tok[1:]
        else:
            paths.append(tok)
    if not recursive:
        return False
    return any(_normalize_rm_target(path) in ("/", "~home", "..") for path in paths)


def _normalize_rm_target(path: str) -> str:
    """Reduce a path to "/", "~home", ".." or itself: ~/ and $HOME/* are the home dir."""
    p = path.strip()
    while p.endswith("/") or p.endswith("*"):
        p = p[:-1]
    if p in _HOME_DIRS:
        return "~home"
    if p == "" and path.strip():
        return "/"
    if re.fullmatch(r"\.\.(/\.\.)*", p):
        return ".."
    return p


def has_clean_fd_flags(args: list[str]) -> bool:
    for arg in args:
        if arg.startswith("-") and "f" in arg and "d" in arg:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
