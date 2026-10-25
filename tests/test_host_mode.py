"""Host mode: an AI app the person already uses writes and judges; Proofhouse checks, records and assembles.

None of this may need an API key or the network. The commands under test are
``proofhouse check``, ``proofhouse record`` and ``proofhouse render video``.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from proofhouse import cli, studio

SITE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Corner Bakery</title></head>'
    '<body><h1>Corner Bakery</h1><a href="menu.html">Menu</a></body></html>'
)
MENU = SITE.replace("Corner Bakery</title>", "Menu</title>").replace('<a href="menu.html">Menu</a>', "<p>Bread</p>")
BROKEN = SITE.replace("menu.html", "missing-page.html")

SERVER = """import json, sys
for line in sys.stdin:
    request = json.loads(line)
    if request.get('method') == 'initialize':
        result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'tiny', 'version': '1'}}
    elif request.get('method') == 'tools/list':
        result = {'tools': [{'name': 'echo', 'inputSchema': {'type': 'object'}}]}
    else:
        continue
    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)
"""
HOOK = "import json, sys\nevent = json.load(sys.stdin)\nprint(event['hook_event_name'])\nsys.exit(2)\n"
SKILL = "---\nname: refund-helper\ndescription: Use when a customer asks for a refund.\n---\n# Refund helper\nCheck the order first.\n"
AGENT = "---\nname: refund-agent\ndescription: Handles refund requests.\n---\nYou handle refunds politely.\n"


@pytest.fixture(autouse=True)
def no_network_and_no_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Host mode must work with no key and no network, so any attempt to connect fails the test."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("host mode tried to use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(Path("no-such-browser")))
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def site(folder: Path, index: str = SITE) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(index, encoding="utf-8")
    (folder / "menu.html").write_text(MENU, encoding="utf-8")
    return folder


def mcp(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "server.py").write_text(SERVER, encoding="utf-8")
    (folder / "manifest.json").write_text(
        json.dumps({"name": "tiny-server", "command": "python", "args": ["server.py"]}), encoding="utf-8")
    return folder


def hook(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "hook.py").write_text(HOOK, encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps({
        "event": "PreToolUse", "matcher": "Bash", "command": "python hook.py",
        "sample_event": {"hook_event_name": "PreToolUse"}}), encoding="utf-8")
    return folder


# ---------------------------------------------------------------- check


def test_check_site_passes_a_good_site(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "site", str(site(tmp_path / "s")), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows and all(row["ok"] is not False for row in rows)
    assert {"check", "ok", "detail"} <= set(rows[0])


def test_check_site_fails_a_broken_link_and_names_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "site", str(site(tmp_path / "s", BROKEN))]) != 0
    out = capsys.readouterr().out
    assert "FAIL" in out and "missing-page.html" in out


def test_check_site_without_a_folder_is_a_clear_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "site", str(tmp_path / "nope")]) != 0
    assert "nope" in capsys.readouterr().err


def test_check_mcp_starts_the_server_only_when_allowed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = mcp(tmp_path / "m")
    assert cli.main(["check", "mcp", str(folder)]) != 0
    assert "--allow-commands" in capsys.readouterr().out
    assert cli.main(["check", "mcp", str(folder), "--allow-commands"]) == 0
    assert "listed 1 tools" in capsys.readouterr().out


def test_check_mcp_needs_the_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "server.py").write_text(SERVER, encoding="utf-8")
    assert cli.main(["check", "mcp", str(folder), "--allow-commands"]) != 0
    assert "manifest.json" in capsys.readouterr().err


def test_check_hook_runs_it_on_the_sample_event(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "hook", str(hook(tmp_path / "h")), "--allow-commands"]) == 0
    assert "PASS" in capsys.readouterr().out


def test_check_hook_rejects_an_unknown_event(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = hook(tmp_path / "h")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    manifest["event"] = "NotAnEvent"
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert cli.main(["check", "hook", str(folder), "--allow-commands"]) != 0
    assert "unknown event" in capsys.readouterr().out


def test_check_rule_installs_and_removes_on_every_tool(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    rule = tmp_path / "safe-edits.md"
    rule.write_text("# Safe edits\nRead a file before changing it.\n", encoding="utf-8")
    assert cli.main(["check", "rule", str(rule)]) == 0
    out = capsys.readouterr().out
    assert "claude" in out and "cursor" in out and "codex" in out


def test_check_skill_and_agent_use_the_installers_own_rules(tmp_path: Path) -> None:
    skill = tmp_path / "refund-helper"
    skill.mkdir()
    (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
    assert cli.main(["check", "skill", str(skill)]) == 0
    (skill / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    assert cli.main(["check", "skill", str(skill)]) != 0
    agent = tmp_path / "refund-agent.md"
    agent.write_text(AGENT, encoding="utf-8")
    assert cli.main(["check", "agent", str(agent)]) == 0
    agent.write_text("You handle refunds.\n", encoding="utf-8")
    assert cli.main(["check", "agent", str(agent)]) != 0


def test_check_refuses_a_link_that_points_outside_the_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = mcp(tmp_path / "m")
    outside = tmp_path / "outside.py"
    outside.write_text("print('x')", encoding="utf-8")
    try:
        (folder / "link.py").symlink_to(outside)
    except OSError:
        pytest.skip("this machine does not allow symbolic links")
    assert cli.main(["check", "mcp", str(folder), "--allow-commands"]) != 0
    assert "link" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------- record


def record(tmp_path: Path, kind: str, source: Path, *extra: str) -> int:
    return cli.main(["record", kind, str(source), "--out", str(tmp_path / "out"), "--request", "a useful thing",
                     "--agent", "cursor", *extra])


def saved(tmp_path: Path) -> dict[str, object]:
    return json.loads((tmp_path / "out" / "record.json").read_text(encoding="utf-8"))


def test_record_keeps_every_version_and_delivers_the_best_site(tmp_path: Path) -> None:
    assert record(tmp_path, "site", site(tmp_path / "s1"), "--score", "6") == 0
    assert record(tmp_path, "site", site(tmp_path / "s2"), "--score", "8") == 0
    out = tmp_path / "out"
    assert (out / "v1" / "site" / "index.html").is_file() and (out / "v2" / "site" / "index.html").is_file()
    assert (out / "v1" / "checks.json").is_file()
    assert (out / "site" / "index.html").is_file()
    data = saved(tmp_path)
    assert data["schema"] == "proofhouse.host/v1" and data["best_version"] == 2 and data["agent"] == "cursor"
    assert [r["version"] for r in data["rounds"]] == [1, 2] and [r["score"] for r in data["rounds"]] == [6, 8]
    assert "advice" in str(data["judge_note"])


def test_a_version_that_fails_its_checks_never_beats_one_that_passes(tmp_path: Path) -> None:
    # A failing version is still kept (every version is kept), but it can never be the delivered one.
    assert record(tmp_path, "site", site(tmp_path / "bad", BROKEN), "--score", "9") == 0
    assert (tmp_path / "out" / "v1" / "site" / "index.html").is_file()
    assert saved(tmp_path)["best_version"] is None
    assert not (tmp_path / "out" / "site").exists()
    assert record(tmp_path, "site", site(tmp_path / "good"), "--score", "6") == 0
    data = saved(tmp_path)
    assert data["best_version"] == 2 and data["rounds"][0]["passed"] is False
    assert 'href="menu.html"' in (tmp_path / "out" / "site" / "index.html").read_text(encoding="utf-8")


def test_record_prompt_copy_skill_agent_and_rule_use_makes_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    prompt = tmp_path / "prompt.md"
    prompt.write_text("You are a support agent.\n", encoding="utf-8")
    assert record(tmp_path, "prompt", prompt, "--score", "8") == 0
    assert (tmp_path / "out" / "v1.md").read_text(encoding="utf-8") == "You are a support agent.\n"
    assert (tmp_path / "out" / "final.md").read_text(encoding="utf-8") == "You are a support agent.\n"

    skill = tmp_path / "refund-helper"
    skill.mkdir()
    (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
    skill_out = tmp_path / "skill-out"
    assert cli.main(["record", "skill", str(skill), "--out", str(skill_out), "--request", "x", "--agent", "codex"]) == 0
    assert (skill_out / "refund-helper" / "SKILL.md").read_text(encoding="utf-8") == SKILL

    agent = tmp_path / "refund-agent.md"
    agent.write_text(AGENT, encoding="utf-8")
    agent_out = tmp_path / "agent-out"
    assert cli.main(["record", "agent", str(agent), "--out", str(agent_out), "--request", "x", "--agent", "codex"]) == 0
    assert (agent_out / "refund-agent.md").is_file()

    rule = tmp_path / "safe-edits.md"
    rule.write_text("# Safe edits\nRead first.\n", encoding="utf-8")
    rule_out = tmp_path / "rule-out"
    assert cli.main(["record", "rule", str(rule), "--out", str(rule_out), "--request", "x", "--agent", "codex"]) == 0
    assert (rule_out / "safe-edits.md").is_file()


def test_record_mcp_and_hook_deliver_install_help(tmp_path: Path) -> None:
    assert record(tmp_path, "mcp", mcp(tmp_path / "m"), "--allow-commands") == 0
    out = tmp_path / "out"
    assert (out / "mcp" / "server.py").is_file()
    assert "proofhouse install mcp tiny-server" in (out / "INSTALL-MCP.txt").read_text(encoding="utf-8")
    hook_out = tmp_path / "hook-out"
    assert cli.main(["record", "hook", str(hook(tmp_path / "h")), "--out", str(hook_out), "--request", "x",
                     "--agent", "cursor", "--allow-commands"]) == 0
    snippet = json.loads((hook_out / "settings-snippet.json").read_text(encoding="utf-8"))
    assert snippet["hooks"]["PreToolUse"][0]["matcher"] == "Bash"


def test_record_says_so_when_a_check_was_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    record(tmp_path, "mcp", mcp(tmp_path / "m"), "--json")
    summary = json.loads(capsys.readouterr().out)
    assert summary["version"] == 1 and summary["checks_not_run"] == 1


@pytest.mark.parametrize("score", ["11", "-1", "nine"])
def test_record_refuses_a_score_outside_0_to_10(tmp_path: Path, score: str) -> None:
    with pytest.raises(SystemExit):
        record(tmp_path, "site", site(tmp_path / "s"), "--score", score)
    assert not (tmp_path / "out").exists()


def test_record_needs_something_to_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert record(tmp_path, "site", tmp_path / "missing") != 0
    assert "missing" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------- render video

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg is not installed")


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def video_folder(tmp_path: Path, with_voice: bool = True) -> Path:
    folder = tmp_path / "v"
    folder.mkdir()
    ffmpeg("-f", "lavfi", "-i", "color=c=red:s=320x240", "-frames:v", "1", str(folder / "shot-01.png"))
    ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x240", "-frames:v", "1", str(folder / "shot-02.png"))
    script: dict[str, object] = {
        "title": "Corner Bakery", "voiceover": "Fresh bread every morning.", "music": "",
        "shots": [{"seconds": 2, "visual": "red", "caption": "Fresh bread", "file": "shot-01.png"},
                  {"seconds": 2, "visual": "blue", "caption": "Every morning", "file": "shot-02.png"}],
    }
    if with_voice:
        ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=4", str(folder / "voice.wav"))
        script["voice_file"] = "voice.wav"
    (folder / "script.json").write_text(json.dumps(script), encoding="utf-8")
    return folder


@needs_ffmpeg
def test_render_video_assembles_the_agents_shots_voice_and_captions(tmp_path: Path) -> None:
    folder = video_folder(tmp_path)
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) == 0
    video = folder / "video-1x1.mp4"
    measured = studio.probe(video)
    assert abs(measured["seconds"] - 4) < 0.5 and measured["audio"] is True
    assert "Fresh bread" in (folder / "captions.srt").read_text(encoding="utf-8")
    record = json.loads((folder / "studio.json").read_text(encoding="utf-8"))
    assert record["spent_usd_estimated"] == "0" and not record["calls"]
    assert all(check["ok"] for check in record["checks"])


@needs_ffmpeg
def test_render_video_without_voice_is_silent_and_still_passes(tmp_path: Path) -> None:
    folder = video_folder(tmp_path, with_voice=False)
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) == 0
    assert studio.probe(folder / "video-1x1.mp4")["audio"] is False


@needs_ffmpeg
def test_render_video_names_a_missing_shot_and_renders_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = video_folder(tmp_path)
    (folder / "shot-02.png").unlink()
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) != 0
    assert "shot-02.png" in capsys.readouterr().err
    assert not list(folder.glob("video-*.mp4"))


@needs_ffmpeg
def test_render_video_refuses_a_script_with_no_shots(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "v"
    folder.mkdir()
    (folder / "script.json").write_text(json.dumps({"title": "x", "shots": []}), encoding="utf-8")
    assert cli.main(["render", "video", str(folder)]) != 0
    assert "no shots" in capsys.readouterr().err


# ---------------------------------------------------------------- skill that teaches the loop

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "proofhouse-host"


def test_the_host_skill_exists_and_the_installer_accepts_it() -> None:
    from proofhouse.optimize.install_skill import check_frontmatter

    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert check_frontmatter(text) == "proofhouse-host"


def test_the_host_skill_teaches_the_whole_loop_without_a_key() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("proofhouse check", "proofhouse record", "proofhouse render video", "no API key", "second"):
        assert needle in text
    for kind in ("site", "mcp", "hook", "rule", "skill", "agent", "prompt", "video"):
        assert kind in text
