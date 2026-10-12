"""Install agents, rules and MCP servers into Claude Code, Cursor, Codex or any tool; remove only what Proofhouse wrote."""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from proofhouse import cli, hosts

AGENT = "---\nname: review-bot\ndescription: Reviews pull requests for security issues.\n---\nCheck every diff for secrets.\n"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: folder))
    return folder


def ph(argv: list[str]) -> int:
    return cli.main(argv, prog="proofhouse")


def test_a_subagent_goes_into_claude_code_and_comes_out_clean(home: Path, tmp_path: Path) -> None:
    (tmp_path / "agent.md").write_text(AGENT, encoding="utf-8")
    assert ph(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"]) == 0
    placed = home / ".claude" / "agents" / "review-bot.md"
    assert placed.read_text(encoding="utf-8") == AGENT
    assert ph(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"]) == 0  # twice changes nothing
    assert ph(["uninstall", "agent", "review-bot", "--from", "claude"]) == 0
    assert not placed.exists()


def test_a_rule_is_a_marked_block_that_leaves_your_own_text_alone(home: Path, tmp_path: Path) -> None:
    mine = home / ".claude" / "CLAUDE.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("# My own rules\nBe brief.\n", encoding="utf-8")
    (tmp_path / "house-style.md").write_text("Use plain words.", encoding="utf-8")
    assert ph(["install", "rule", str(tmp_path / "house-style.md"), "--into", "claude"]) == 0
    text = mine.read_text(encoding="utf-8")
    assert text.startswith("# My own rules\nBe brief.\n") and "<!-- proofhouse:begin house-style -->\nUse plain words.\n" in text
    assert ph(["uninstall", "rule", "house-style", "--from", "claude"]) == 0
    assert mine.read_text(encoding="utf-8") == "# My own rules\nBe brief.\n"


def test_a_cursor_rule_gets_its_frontmatter_in_the_project(home: Path, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (tmp_path / "style.md").write_text("Use plain words.", encoding="utf-8")
    assert ph(["install", "rule", str(tmp_path / "style.md"), "--into", "cursor", "--project", str(project)]) == 0
    rule = project / ".cursor" / "rules" / "style.mdc"
    assert rule.read_text(encoding="utf-8").startswith("---\ndescription: style\nalwaysApply: true\n---\nUse plain words.")
    assert ph(["install", "rule", str(tmp_path / "style.md"), "--into", "cursor"]) == 2  # Cursor rules live in a project


def test_mcp_servers_go_into_json_and_toml_and_leave_other_servers_alone(home: Path, tmp_path: Path) -> None:
    cursor_cfg = home / ".cursor" / "mcp.json"
    cursor_cfg.parent.mkdir(parents=True)
    cursor_cfg.write_text(json.dumps({"mcpServers": {"theirs": {"command": "x"}}}), encoding="utf-8")
    assert ph(["install", "mcp", "files", "--into", "cursor", "--command", "npx", "--arg=-y", "--arg", "server-files",
               "--env", "ROOT=/data"]) == 0
    servers = json.loads(cursor_cfg.read_text(encoding="utf-8"))["mcpServers"]
    assert servers["files"] == {"command": "npx", "args": ["-y", "server-files"], "env": {"ROOT": "/data"}} and "theirs" in servers
    assert ph(["install", "mcp", "theirs", "--into", "cursor", "--command", "y"]) == 2  # not ours: refused
    assert ph(["uninstall", "mcp", "files", "--from", "cursor"]) == 0
    assert json.loads(cursor_cfg.read_text(encoding="utf-8")) == {"mcpServers": {"theirs": {"command": "x"}}}

    assert ph(["install", "mcp", "files", "--into", "codex", "--command", "npx", "--arg", "server-files"]) == 0
    codex = home / ".codex" / "config.toml"
    assert tomllib.loads(codex.read_text(encoding="utf-8"))["mcp_servers"]["files"] == {"command": "npx", "args": ["server-files"]}
    assert ph(["uninstall", "mcp", "files", "--from", "codex"]) == 0
    assert not codex.exists()  # Proofhouse created it, and it is empty again


def test_claude_code_mcp_lives_in_the_project(home: Path, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    assert ph(["install", "mcp", "db", "--into", "claude", "--project", str(project), "--command", "db-server"]) == 0
    assert json.loads((project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["db"]["command"] == "db-server"


def test_your_edits_are_never_overwritten_or_removed_silently(home: Path, tmp_path: Path) -> None:
    (tmp_path / "agent.md").write_text(AGENT, encoding="utf-8")
    placed = home / ".claude" / "agents" / "review-bot.md"
    placed.parent.mkdir(parents=True)
    placed.write_text("my own agent\n", encoding="utf-8")
    assert ph(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"]) == 2
    assert ph(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude", "--force"]) == 0
    placed.write_text(AGENT + "my edit\n", encoding="utf-8")
    assert ph(["uninstall", "agent", "review-bot", "--from", "claude"]) == 2
    assert ph(["uninstall", "agent", "review-bot", "--from", "claude", "--force"]) == 0
    assert placed.read_text(encoding="utf-8") == "my own agent\n"  # the copy kept before --force comes back


@pytest.mark.parametrize("name", ["../evil", "Evil", "a/b", "", "x" * 70])
def test_names_cannot_escape_the_target_folder(home: Path, name: str) -> None:
    with pytest.raises(hosts.HostError):
        hosts.target("claude", "agent", name, None)


def test_any_other_tool_is_one_entry_in_your_hosts_file(home: Path, tmp_path: Path) -> None:
    (hosts.proofhouse_home()).mkdir(parents=True, exist_ok=True)
    (hosts.proofhouse_home() / "hosts.json").write_text(json.dumps({"schema": "proofhouse.hosts/v1", "hosts": [
        {"id": "windsurf", "name": "Windsurf", "rule": {"user": "~/.windsurf/rules/{name}.md", "format": "file"}}]}), encoding="utf-8")
    (tmp_path / "style.md").write_text("Use plain words.", encoding="utf-8")
    assert ph(["install", "rule", str(tmp_path / "style.md"), "--into", "windsurf"]) == 0
    assert (home / ".windsurf" / "rules" / "style.md").read_text(encoding="utf-8") == "Use plain words.\n"
