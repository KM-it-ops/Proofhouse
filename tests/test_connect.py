"""`proofhouse connect`: one step puts Proofhouse inside the AI apps on the machine, and --undo takes it out."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import connect, providers
from proofhouse.mcp_server import Tools


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A pretend home folder and Proofhouse settings folder; nothing real is read or written."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    monkeypatch.delenv("PROOFHOUSE_AGENT_TOKEN", raising=False)
    return home


def _which(*present: str):
    return lambda name: f"/bin/{name}" if name in present else None


class Commands:
    def __init__(self, code: int = 0, text: str = ""):
        self.ran: list[list[str]] = []
        self.code, self.text = code, text

    def __call__(self, argv: list[str]) -> tuple[int, str]:
        self.ran.append(argv)
        return self.code, self.text


def _go(which, run=None) -> tuple[int, str, Commands]:
    run = run or Commands()
    lines: list[str] = []
    code = connect.connect(which=which, run=run, say=lines.append)
    return code, "\n".join(lines), run


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_no_app_on_the_machine_says_so_and_changes_nothing(machine, tmp_path):
    code, text, run = _go(_which())
    assert code == 1 and "No AI app was found" in text and "demo make" in text
    assert run.ran == [] and _snapshot(machine) == {} and not (tmp_path / "ph" / "connect.json").exists()


def test_each_app_gets_the_tools_and_the_skill_and_the_logged_in_agents_become_providers(machine):
    which = _which("claude", "cursor", "codex", "proofhouse")
    code, text, run = _go(which)
    assert code == 0, text

    # Claude Code: registered through its own command, for every project, with itself as the writer
    assert run.ran == [["claude", "mcp", "add", "--scope", "user", "proofhouse", "--",
                        "/bin/proofhouse", "mcp", "--agent", "claude"]]
    assert (machine / ".claude" / "skills" / "proofhouse" / "SKILL.md").is_file()

    # Cursor: its own settings file; it has no command-line agent of its own, so no --agent
    cursor = json.loads((machine / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert cursor["mcpServers"]["proofhouse"] == {"command": "/bin/proofhouse", "args": ["mcp"]}
    assert (machine / ".cursor" / "skills" / "proofhouse" / "SKILL.md").is_file()

    # Codex: a marked block in its settings file, and a plain word that it has no skills folder
    codex = (machine / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.proofhouse]" in codex and '"--agent", "codex"' in codex
    assert "Codex has no skills folder" in text

    for agent in ("claude", "codex"):
        profile = providers.find(f"agent-{agent}")
        assert profile is not None and profile.local
    assert providers.find("agent-grok") is None  # not installed, so not declared
    assert "logged-in claude, and codex judges it" in text and "connect --undo" in text

    # the chat tools now pick the app's own agent as the writer and the other one as the judge
    tools = Tools(agent="codex", which=which)
    assert tools._writer(None, None) == ("agent-codex", "default")
    assert tools._judge("agent-codex", None) == "agent-claude/default"


def test_running_it_twice_changes_nothing_more(machine):
    which = _which("cursor", "codex", "proofhouse")
    assert _go(which)[0] == 0
    before = _snapshot(machine)
    code, text, _ = _go(which)
    assert code == 0 and "already" in text
    assert _snapshot(machine) == before


def test_undo_leaves_the_apps_as_they_were(machine, tmp_path):
    (machine / ".cursor").mkdir()
    mine = json.dumps({"mcpServers": {"other": {"command": "x"}}}, indent=2) + "\n"
    (machine / ".cursor" / "mcp.json").write_text(mine, encoding="utf-8")
    (machine / ".codex").mkdir()
    (machine / ".codex" / "config.toml").write_text('model = "o"\n', encoding="utf-8")
    before = _snapshot(machine)

    which = _which("claude", "cursor", "codex", "proofhouse")
    assert _go(which)[0] == 0
    assert _snapshot(machine) != before

    run, lines = Commands(), []
    assert connect.undo(run=run, say=lines.append) == 0, lines
    assert run.ran == [["claude", "mcp", "remove", "--scope", "user", "proofhouse"]]
    after = _snapshot(machine)
    assert {k: v for k, v in after.items() if "backup" not in k.lower()} == before
    assert providers.find("agent-claude") is None and providers.find("agent-codex") is None
    assert not (tmp_path / "ph" / "connect.json").exists()

    lines.clear()
    assert connect.undo(run=Commands(), say=lines.append) == 0 and "Nothing to undo" in lines[0]


def test_what_was_yours_before_is_not_taken_over_and_not_removed(machine):
    data = providers.load_user()
    yours = {"id": "agent-claude", "base_url": "http://127.0.0.1:9999/v1"}
    data["providers"].append(yours)
    providers.save_user(data)
    skill = machine / ".claude" / "skills" / "proofhouse"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("mine", encoding="utf-8")

    code, text, _ = _go(_which("claude", "proofhouse"), Commands(1, "MCP server proofhouse already exists in user config"))
    assert code == 0 and "already there; left as it is" in text and "already has a server named proofhouse" in text

    run = Commands()
    connect.undo(run=run, say=lambda line: None)
    assert run.ran == []  # connect did not register it, so undo does not remove it
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == "mine"
    assert providers.find("agent-claude").base_url == "http://127.0.0.1:9999/v1"


def test_a_failed_registration_is_said_plainly_and_the_exit_code_shows_it(machine):
    code, text, _ = _go(_which("claude", "proofhouse"), Commands(1, "claude is not logged in"))
    assert code == 1 and "tools NOT registered: claude is not logged in" in text
