"""Prove `proofhouse install` and `proofhouse uninstall` on a throwaway folder.

Run from the repository root:  uv run --no-sync python examples/host-mode/install/prove.py

Everything happens inside one temporary folder. HOME, USERPROFILE and PROOFHOUSE_HOME point into it,
and every install passes --project, so no real settings, shell profile or ~/.claude is read or written.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent
WORK = Path(tempfile.mkdtemp(prefix="proofhouse-install-")).resolve()
PROJECT = WORK / "project"
ENV = {**os.environ, "HOME": str(WORK / "home"), "USERPROFILE": str(WORK / "home"), "PROOFHOUSE_HOME": str(WORK / "ph-home")}
failures: list[str] = []


def show(text: str) -> None:
    for form in (str(WORK), str(WORK).replace("\\", "/")):
        text = text.replace(form, "<target>")
    print(text.rstrip())


def run(*args: str) -> subprocess.CompletedProcess[str]:
    shown = " ".join(("<target>" if a == str(PROJECT) else Path(a).name if Path(a).is_absolute() else a) for a in args)
    print(f"\n$ proofhouse {shown}")
    done = subprocess.run(["proofhouse", *args], capture_output=True, text=True, env=ENV, cwd=WORK)
    show((done.stdout or "") + (done.stderr or "") + f"[exit {done.returncode}]")
    return done


def expect(ok: bool, what: str) -> None:
    print(f"  {'PASS' if ok else 'FAIL'}: {what}")
    if not ok:
        failures.append(what)


def tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in sorted(root.rglob("*")) if p.is_file()}


def rpc(proc: subprocess.Popen[str], message: dict[str, object]) -> dict[str, object]:
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def installed_server_answers() -> bool:
    config = json.loads((PROJECT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["unit-desk"]
    proc = subprocess.Popen([config["command"], *config["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=PROJECT, env=ENV)
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "prove", "version": "1"}}})
        names = [t["name"] for t in rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
        answer = rpc(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "days_between", "arguments": {"start": "2026-10-25", "end": "2026-11-15"}}})
        text = json.dumps(answer["result"])
        print(f"  server tools: {names}; days_between 2026-10-25 -> 2026-11-15 = {text[:120]}")
        return "days_between" in names and "21" in text
    finally:
        proc.kill()


def main() -> None:
    assert str(WORK).startswith(str(Path(tempfile.gettempdir()).resolve())), "work folder is not in the system temp folder"
    PROJECT.mkdir(parents=True)
    claude_md = PROJECT / "CLAUDE.md"
    claude_md.write_text("# My own project notes\n\nKeep these lines.\n", encoding="utf-8")
    (PROJECT / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "echo", "args": []}}}, indent=2) + "\n", encoding="utf-8")
    (PROJECT / "tools" / "unit-desk").mkdir(parents=True)
    shutil.copy(EXAMPLES / "mcp" / "server.py", PROJECT / "tools" / "unit-desk" / "server.py")
    agent, rule = HERE / "release-notes-writer.md", EXAMPLES / "rule" / "safe-database-migrations.md"
    agent_path = PROJECT / ".claude" / "agents" / "release-notes-writer.md"
    # the server copy belongs to the user's project, not to install, so it is left out of the before/after comparison
    before = {k: v for k, v in tree(WORK).items() if not k.startswith("project/tools/")}
    print(f"throwaway target: <target>  ({len(before)} files before)")
    for name, digest in before.items():
        print(f"  before  {digest}  {name}")

    print("\n== INSTALL ==")
    p = str(PROJECT)
    run("hosts", "list")
    run("install", "agent", str(agent), "--into", "claude", "--project", p)
    run("install", "rule", str(rule), "--into", "claude", "--project", p)
    run("install", "rule", str(rule), "--into", "cursor", "--project", p)
    run("install", "mcp", "unit-desk", "--into", "claude", "--project", p, "--command", "python", "--arg", "tools/unit-desk/server.py")
    again = run("install", "agent", str(agent), "--into", "claude", "--project", p)
    expect("nothing changed" in again.stdout, "installing the same agent twice changes nothing")
    for path in (".claude/agents/release-notes-writer.md", ".cursor/rules/safe-database-migrations.mdc"):
        expect((PROJECT / path).is_file(), f"{path} exists")
    notes = claude_md.read_text(encoding="utf-8")
    expect("proofhouse:begin safe-database-migrations" in notes and "Keep these lines." in notes, "CLAUDE.md holds the rule block and still holds the user's own lines")
    servers = json.loads((PROJECT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    expect(set(servers) == {"other", "unit-desk"}, "the MCP entry was added next to the user's own server")

    print("\n== DOES THE INSTALLED THING WORK? ==")
    expect(installed_server_answers(), "the MCP server started from the installed config answers tools/list and tools/call")
    agent_text = agent_path.read_text(encoding="utf-8")
    expect(agent_text.startswith("---\nname: release-notes-writer\n") and "description:" in agent_text, "the installed agent has the frontmatter Claude Code reads")
    installed = {k: v for k, v in tree(WORK).items() if not k.startswith("project/tools/")}
    print("\nwhat install added or changed:")
    for name, digest in installed.items():
        if before.get(name) != digest:
            print(f"  {'changed' if name in before else 'new    '}  {name}")

    print("\n== UNINSTALL ==")
    agent_path.write_text(agent_text + "\nmy edit\n", encoding="utf-8")
    refused = run("uninstall", "agent", "release-notes-writer", "--from", "claude", "--project", p)
    expect(refused.returncode != 0 and agent_path.is_file(), "an agent edited since install is not removed without --force")
    run("uninstall", "agent", "release-notes-writer", "--from", "claude", "--project", p, "--force")
    run("uninstall", "rule", "safe-database-migrations", "--from", "claude", "--project", p)
    run("uninstall", "rule", "safe-database-migrations", "--from", "cursor", "--project", p)
    run("uninstall", "mcp", "unit-desk", "--from", "claude", "--project", p)
    records = WORK / "ph-home" / "installs"
    expect(not records.exists() or not list(records.iterdir()), "no install records are left")
    after = {k: v for k, v in tree(WORK).items() if not k.startswith("project/tools/") and not k.startswith("ph-home/install-backups/")}
    expect(after == before, "every file is byte-for-byte what it was before the install: nothing added, nothing left")
    leftover_dirs = [d.relative_to(WORK).as_posix() for d in (PROJECT / ".claude", PROJECT / ".cursor") if d.exists() and not any(d.rglob("*.*"))]
    print(f"  empty folders left behind (no files inside): {leftover_dirs or 'none'}")
    backups = WORK / "ph-home" / "install-backups"
    print(f"  backup copies kept in the Proofhouse home: {len(list(backups.iterdir())) if backups.exists() else 0}")


try:
    main()
finally:
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"\nthrowaway target removed: {not WORK.exists()}")

print("\nRESULT:", "FAILED: " + "; ".join(failures) if failures else "all checks passed")
sys.exit(1 if failures else 0)
