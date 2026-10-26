"""Standalone tests for guard.py — run: python test_guard.py (exit 0 on success)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "guard.py"

MUST_BLOCK = [
    "git push --force origin main",
    "git -C repo push --force origin main",
    "git -c core.editor=true push -f origin main",
    "git push -uf origin main",
    "git commit -m ok\ngit push --force origin main",
    "rm -rf /*",
    "rm -rf ~/",
    "rm -rf $HOME/",
    'rm -rf "$HOME"',
    "rm -fr /",
    "bash -c 'git push --force origin main'",
    "sh -c 'rm -rf ~'",
    "env GIT_TRACE=1 git push -f origin main",
    "echo 'drop table users' | psql mydb",
    "psql -c 'DROP DATABASE prod'",
    "git reset --hard HEAD~1 && git push origin main",
    "git push origin +main",
    "sudo git push --force origin main",
    "(git push --force origin main)",
    "git push --force origin main &",
    "xargs -I{} git push --force {} origin",
    "git --no-pager push --force origin main",
    'rm -rf "/"',
    "time git push -f origin main",
    "nohup git push --force origin main &",
    "if true; then git push -f origin main; fi",
    "git push origin main --force",
    "cd repo && git push -fu origin main",
    "echo x | sudo -u root git push --force origin main",
    "mysql -e 'DROP DATABASE shop'",
    "git clean -fdx && git push origin main",
    "{ git push -f origin main; }",
]

MUST_ALLOW = [
    "git push origin feat/x",
    "git push --force-with-lease origin feat/x",
    "git push --force-with-lease=main origin main",
    "git commit -m 'never git push --force again'",
    'git commit -m "docs: explain rm -rf / is bad"',
    "rm -rf node_modules",
    "rm -rf ./build /tmp/x",
    "ls -la",
    "git status",
    "echo hi && git log --oneline",
    "git push -u origin feat/x",
    "git -C repo status",
    "git -C repo push origin feat/x",
    "grep -r 'drop table' docs/",
    "git log --grep='push --force'",
    "git push origin feat/x && echo done",
    "rm -rf ./dist ./.cache",
    "rm -r build",
    "psql -c 'select 1'",
    "git diff HEAD~1 | head -20",
    'python -c "print(\'git push -f\')"',
    "printf '%s' 'harmless'",
]

BAD_INPUT = [
    "",
    "not json",
    "[]",
    '{"tool_name":"Bash"}',
    '{"tool_name":"Bash","tool_input":{"command":5}}',
    '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"x"}}',
]

# Extra cases from self-review (evasions we accept may pass; documented in README Limits)
EVASION_SHOULD_ALLOW = [
    "git push --forc origin main",
    "echo Z2l0IHB1c2ggLS1mb3JjZSBvcmlnaW4gbWFpbg== | base64 -d | bash",
    "alias gp='git push --force'; gp origin main",
]


def run_guard(command: str | None, raw: str | None = None) -> int:
    payload = raw if raw is not None else json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }
    )
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode


def main() -> int:
    errors: list[str] = []

    for cmd in MUST_BLOCK:
        rc = run_guard(cmd)
        if rc != 2:
            errors.append(f"should block (exit 2), got {rc}: {cmd!r}")

    for cmd in MUST_ALLOW:
        rc = run_guard(cmd)
        if rc != 0:
            errors.append(f"should allow (exit 0), got {rc}: {cmd!r}")

    for raw in BAD_INPUT:
        proc = subprocess.run(
            [sys.executable, str(GUARD)],
            input=raw,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            errors.append(f"bad input must allow, got {proc.returncode}: {raw!r}")

    for cmd in EVASION_SHOULD_ALLOW:
        rc = run_guard(cmd)
        if rc != 0:
            errors.append(f"evasion case should stay allowed, got {rc}: {cmd!r}")

    if errors:
        print("test_guard.py FAILED:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    print(f"test_guard.py OK: {len(MUST_BLOCK)} block, {len(MUST_ALLOW)} allow, {len(BAD_INPUT)} bad-input cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
