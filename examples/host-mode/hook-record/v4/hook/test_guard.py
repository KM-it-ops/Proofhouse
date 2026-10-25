"""Standalone tests for guard.py — run: python test_guard.py (exit 0 on success)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "guard.py"

MUST_BLOCK = [
    # added after an independent review: absolute paths, -lc, substitutions, sudo options
    "/usr/bin/git push --force origin main",
    "/bin/bash -c 'git push -f origin main'",
    "bash -lc 'git push -f origin main'",
    "echo $(git push -f origin main)",
    "`git push -f origin main`",
    "sudo -u root rm -rf /",
    "sudo -E git push -f origin main",
    "eval git push -f",
    "exec git push -f",
    "bash -c 'bash -c \"git push -f\"'",
    "rm -rf ..",
    "rm -r /",
    "psql <<< 'drop table users'",
    "mysql <<EOF\ndrop table x\nEOF",
    "cd /tmp; psql -c 'DROP TABLE x'",
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
    # second independent review: quoted VAR= prefixes, sudo option clusters, more wrappers
    'GIT_SSH_COMMAND="ssh -i ~/.ssh/deploy_key" git push --force origin main',
    'PGOPTIONS="-c x" psql -c "DROP TABLE t"',
    'FOO="a b" rm -rf ~',
    'sudo -iu postgres psql -c "DROP DATABASE app"',
    "sudo --user root rm -rf /",
    "timeout 120 git push --force origin main",
    "time -p rm -rf ~",
    "nice -n 5 git push -f origin main",
    "stdbuf -oL git push -f origin main",
    "env -u FOO git push -f origin main",
    "(cd app && git push origin main --force)",
    "(cd /tmp && rm -rf ~)",
    "(git push -f origin main && echo hi)",
    'bash -o pipefail -c "git push --force origin main"',
    'bash -euo pipefail -c "git push --force origin main"',
    "rm -rf ../..",
    "rm -rf ../../",
    'rm -rf "$USERPROFILE"',
    'psql.exe -c "DROP TABLE users"',
    "git.exe push -f",
    r'"C:\Program Files\Git\cmd\git.exe" push -f',
    r'echo "C:\\" && git push --force',
    "git push \\\n--force origin main",
    "echo $(echo $(git push -f origin main))",
    # here-documents that the shell or a database shell runs
    "bash <<'EOF'\ngit push -f origin main\nEOF",
    "cat <<EOF | bash\ngit push -f origin main\nEOF",
    "psql app <<'SQL'\nDROP TABLE users;\nSQL",
    "cat <<EOF\n$(git push -f origin main)\nEOF",
    "psql <<EOF\ndrop table x",
    # nesting too deep to inspect is blocked, not waved through
    "(" * 500 + "git push -f" + ")" * 500,
    "eval " * 500 + "git push -f",
    # non-ASCII text must not hide a force-push
    'git commit -m "修正" && git push --force',
    # U+0141 is bytes C5 81 in UTF-8: 0x81 is undefined in Windows cp1252, so a text-mode
    # read of stdin raised and the old guard let the whole command through
    'git commit -m "Łódź" && git push --force',
]

MUST_ALLOW = [
    "rm -rf ~/projects/app/build",
    "rm -rf $HOME/projects/app/build",
    "rm -rf ~/.cache/pip",
    "rm -rf /tmp/build-123/",
    "rm -rf ./",
    "echo git push --force is dangerous",
    'git commit -m "docs: never drop table in psql"',
    "cat docs/psql.md | grep -i 'drop table'",
    "git push origin feat/uf-fix",
    "git -c user.name=force push origin feat/x",
    "sudo -u postgres psql -c 'select 1'",
    "psql -c 'select 1'; git commit -m 'drop table docs'",
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
    # here-document bodies and quoted text are data
    "cat > NOTES.md <<'EOF'\ngit push --force is now blocked\nEOF",
    "git commit -F - <<'EOF'\nrm -rf ~ is bad\nEOF",
    "git commit -m \"$(cat <<'EOF'\nfeat: stop rm -rf ~ in hooks\nEOF\n)\"",
    "gh pr create --body \"$(cat <<'EOF'\n- blocks `git push --force`\nEOF\n)\"",
    'sqlite3 app.db .dump | grep -c "DROP TABLE"',
    "psql app <<'SQL'\nSELECT 1;\nSQL\necho \"todo: drop table legacy\"",
    "git commit -m 'use `git push --force` carefully'",
    'git commit -m "ā"',
]

BAD_INPUT = [
    "",
    "not json",
    "[]",
    "[" * 100000,
    '﻿{"tool_name":"Read"}',
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
        },
        ensure_ascii=False,
    )
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload.encode("utf-8"),
        capture_output=True,
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
            input=raw.encode("utf-8"),
            capture_output=True,
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
