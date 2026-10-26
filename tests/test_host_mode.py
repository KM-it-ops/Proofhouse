"""Host mode: an AI app the person already uses writes and judges; Proofhouse checks, records and assembles.

None of this may need an API key or the network. The commands under test are
``proofhouse check``, ``proofhouse record`` and ``proofhouse render video``.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from proofhouse import cli, host, studio

def _site_blurb() -> str:
    return " ".join(f"fresh loaf {i}" for i in range(1, 28)) + " Baked at 5 AM daily."


SITE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Corner Bakery</title></head>'
    f'<body><h1>Corner Bakery</h1><p>{_site_blurb()}</p><a href="menu.html">Menu</a></body></html>'
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
HOOK = "import json, sys\nevent = json.load(sys.stdin)\nprint(event['hook_event_name'], file=sys.stderr)\nsys.exit(2)\n"
def _skill_body(heading: str, extra: str) -> str:
    return f"# {heading}\n" + " ".join(f"step {i}" for i in range(1, 58)) + f" {extra}\n"


SKILL = (
    "---\nname: refund-helper\ndescription: Use when a customer asks for a refund.\n---\n"
    + _skill_body("Refund helper", "Check the order first at 5 AM.")
)
AGENT = (
    "---\nname: refund-agent\ndescription: Handles refund requests.\n---\n"
    + _skill_body("Refund agent", "You handle refunds politely at 5 AM.")
)


def _long_copy() -> str:
    return " ".join(f"loaf {i}" for i in range(1, 26)) + " Opens at 5 AM.\n"


def _long_prompt(core: str) -> str:
    pad = " ".join(f"rule{i}" for i in range(1, 36))
    return f"{core} {pad}\n"


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


def test_record_refuses_a_link_that_points_outside_the_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = site(tmp_path / "site")
    secret = tmp_path / "secret.txt"
    secret.write_text("private", encoding="utf-8")
    try:
        (folder / "notes.txt").symlink_to(secret)
    except OSError:
        pytest.skip("this machine does not allow symbolic links")
    code = cli.main(["record", "site", str(folder), "--out", str(tmp_path / "out"), "--request", "x", "--agent", "cursor"])
    assert code != 0
    assert "link" in capsys.readouterr().err.lower()
    assert not (tmp_path / "out" / "v1").exists()


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


def test_each_version_keeps_the_agent_that_wrote_it(tmp_path: Path) -> None:
    out = str(tmp_path / "out")
    base = ["record", "site", "--out", out, "--request", "a useful thing"]
    assert cli.main([*base[:2], str(site(tmp_path / "s1")), *base[2:], "--agent", "cursor", "--score", "9"]) == 0
    assert cli.main([*base[:2], str(site(tmp_path / "s2")), *base[2:], "--agent", "codex", "--score", "6"]) == 0
    data = saved(tmp_path)
    assert [r["agent"] for r in data["rounds"]] == ["cursor", "codex"]
    assert data["best_version"] == 1 and data["agent"] == "cursor"
    # A later call that names no agent must not erase or replace what is already recorded.
    assert host.run_record("site", site(tmp_path / "s3"), out=tmp_path / "out", request="a useful thing", agent=None,
                           score=10, judge=None, judge_score=None, judge_note=None, allow_commands=False, as_json=False) == 0
    data = saved(tmp_path)
    assert [r.get("agent") for r in data["rounds"]] == ["cursor", "codex", None]
    assert data["best_version"] == 3 and data["agent"] == "cursor"


def test_an_old_record_without_per_version_agents_keeps_its_agent(tmp_path: Path) -> None:
    assert record(tmp_path, "site", site(tmp_path / "s1"), "--score", "6") == 0
    path = tmp_path / "out" / "record.json"
    old = saved(tmp_path)
    for row in old["rounds"]:
        del row["agent"]  # records written before each version carried its own agent
    old["agent"] = "windsurf"
    path.write_text(json.dumps(old), encoding="utf-8")
    assert host.run_record("site", site(tmp_path / "s2"), out=tmp_path / "out", request="a useful thing", agent=None,
                           score=5, judge=None, judge_score=None, judge_note=None, allow_commands=False, as_json=False) == 0
    data = saved(tmp_path)
    assert "agent" not in data["rounds"][0] and data["best_version"] == 1 and data["agent"] == "windsurf"


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
    prompt.write_text(_long_prompt("You are a support agent."), encoding="utf-8")
    assert record(tmp_path, "prompt", prompt, "--score", "8") == 0
    prompt_text = prompt.read_text(encoding="utf-8")
    assert (tmp_path / "out" / "v1.md").read_text(encoding="utf-8") == prompt_text
    assert (tmp_path / "out" / "final.md").read_text(encoding="utf-8") == prompt_text

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


def test_record_install_help_holds_no_machine_path(tmp_path: Path) -> None:
    assert record(tmp_path, "mcp", mcp(tmp_path / "m"), "--allow-commands") == 0
    hook_out = tmp_path / "hook-out"
    assert cli.main(["record", "hook", str(hook(tmp_path / "h")), "--out", str(hook_out), "--request", "x",
                     "--agent", "cursor", "--allow-commands"]) == 0
    written = [tmp_path / "out" / "INSTALL-MCP.txt", hook_out / "settings-snippet.json", hook_out / "INSTALL-HOOK.txt"]
    for path in written:
        text = path.read_text(encoding="utf-8")
        assert str(tmp_path) not in text and tmp_path.as_posix() not in text, path.name
        assert "<this-folder>" in text, path.name
    assert "<this-folder>/mcp/server.py" in written[0].read_text(encoding="utf-8")
    assert "<this-folder>/hook/hook.py" in written[1].read_text(encoding="utf-8")


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


@needs_ffmpeg
@pytest.mark.parametrize("shot", ["playlist.m3u8", "shot.txt", "shot"])
def test_render_video_only_opens_picture_video_and_sound_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], shot: str,
) -> None:
    folder = video_folder(tmp_path)
    (folder / shot).write_text("#EXTM3U\nhttps://example.com/a.ts\n", encoding="utf-8")
    script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    script["shots"][0]["file"] = shot
    (folder / "script.json").write_text(json.dumps(script), encoding="utf-8")
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) != 0
    assert "supported" in capsys.readouterr().err
    assert not list(folder.glob("video-*.mp4"))


@needs_ffmpeg
def test_render_video_refuses_a_hard_link_to_a_file_outside_the_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = video_folder(tmp_path)
    outside = tmp_path / "outside.srt"
    outside.write_text("keep me", encoding="utf-8")
    try:
        (folder / "captions.srt").hardlink_to(outside)
    except OSError:
        pytest.skip("this machine does not allow hard links")
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) != 0
    assert "link" in capsys.readouterr().err.lower()
    assert outside.read_text(encoding="utf-8") == "keep me"


# ---------------------------------------------------------------- safety found in review


def test_check_site_does_not_open_a_browser_unless_commands_are_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proofhouse import sitecheck

    fake = tmp_path / "chrome.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(fake))
    opened: list[list[str]] = []

    def record_launch(command: list[str], timeout: int) -> str:
        opened.append(command)
        return "stubbed"

    monkeypatch.setattr(sitecheck, "_open", record_launch)
    folder = site(tmp_path / "s")
    assert cli.main(["check", "site", str(folder)]) == 0
    assert opened == []
    assert cli.main(["check", "site", str(folder), "--allow-commands"]) == 0
    assert opened, "with --allow-commands the site is opened in the browser"


def test_check_site_browser_launch_always_gives_the_browser_a_reason_to_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proofhouse import sitecheck

    fake = tmp_path / "chrome.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(fake))
    opened: list[list[str]] = []

    def record_launch(command: list[str], timeout: int) -> str:
        opened.append(command)
        return "stubbed"

    monkeypatch.setattr(sitecheck, "_open", record_launch)
    assert cli.main(["check", "site", str(site(tmp_path / "s")), "--allow-commands"]) == 0
    assert opened
    for command in opened:  # a headless browser with neither flag never exits on its own
        assert "--dump-dom" in command or any(part.startswith("--screenshot=") for part in command)


def test_check_site_one_size_stuck_is_not_measured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import sitecheck

    fake = tmp_path / "chrome.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(fake))

    def record_launch(command: list[str], timeout: int) -> subprocess.CompletedProcess[str] | str:
        if any(part == "--window-size=1440,900" for part in command):
            return "the browser did not finish in 30 s, twice"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sitecheck, "_open", record_launch)
    row = next(c for c in sitecheck.check_site(site(tmp_path / "s")) if c["check"] == "no JavaScript errors in the browser")
    assert row["ok"] is None
    assert row["ok"] is not True
    assert row["ok"] is not False
    assert "desktop" in row["detail"].lower()


def test_check_site_one_size_stuck_other_errors_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import sitecheck

    fake = tmp_path / "chrome.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(fake))

    def record_launch(command: list[str], timeout: int) -> subprocess.CompletedProcess[str] | str:
        if any(part == "--window-size=1440,900" for part in command):
            return "the browser did not finish in 30 s, twice"
        return subprocess.CompletedProcess(
            args=command, returncode=0, stdout="", stderr="[error] Uncaught Error: boom",
        )

    monkeypatch.setattr(sitecheck, "_open", record_launch)
    row = next(c for c in sitecheck.check_site(site(tmp_path / "s")) if c["check"] == "no JavaScript errors in the browser")
    assert row["ok"] is False


def test_check_site_both_sizes_clean_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import sitecheck

    fake = tmp_path / "chrome.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(fake))

    def record_launch(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sitecheck, "_open", record_launch)
    row = next(c for c in sitecheck.check_site(site(tmp_path / "s")) if c["check"] == "no JavaScript errors in the browser")
    assert row["ok"] is True


def test_browser_output_that_is_not_in_the_console_codepage_does_not_break_the_check(capfd):
    import sys
    from proofhouse import sitecheck
    run = sitecheck._open([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'caf\\xc3\\xa9 \\xe2\\x80\\x9d \\x9d')"], 30)
    assert not isinstance(run, str)
    assert "caf" in run.stdout
    assert "Traceback" not in capfd.readouterr().err


def test_find_browser_finds_edge_at_its_install_folder_when_not_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from proofhouse import sitecheck

    edge = tmp_path / "pf86" / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.write_text("", encoding="utf-8")
    monkeypatch.delenv("PROOFHOUSE_BROWSER", raising=False)
    for name in ("ProgramFiles", "LOCALAPPDATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "pf86"))
    monkeypatch.setattr(sitecheck.shutil, "which", lambda name, *a, **k: None)
    assert sitecheck.find_browser() == str(edge)


@pytest.mark.parametrize("kind", ["rule", "agent"])
def test_record_never_deletes_files_it_did_not_deliver(tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (work / "README.md").write_text("mine", encoding="utf-8")
    source = tmp_path / "thing.md"
    source.write_text(AGENT if kind == "agent" else "Always say please.\n", encoding="utf-8")
    code = cli.main(["record", kind, str(source), "--out", str(work), "--request", "x", "--agent", "cursor"])
    assert code != 0
    assert (work / "README.md").read_text(encoding="utf-8") == "mine"
    assert "out" in capsys.readouterr().err.lower()


def test_record_refuses_an_out_folder_that_holds_or_sits_inside_the_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "proj"
    source = site(project / "site")
    assert cli.main(["record", "site", str(source), "--out", str(project), "--request", "x", "--agent", "cursor"]) != 0
    assert (source / "index.html").read_text(encoding="utf-8") == SITE
    assert cli.main(["record", "site", str(source), "--out", str(source / "rec"), "--request", "x", "--agent", "cursor"]) != 0
    assert not (source / "rec").exists()
    assert capsys.readouterr().err


def test_record_does_not_call_an_unrun_check_a_pass(tmp_path: Path) -> None:
    assert record(tmp_path, "mcp", mcp(tmp_path / "m")) == 0
    out = tmp_path / "out"
    saved_record = json.loads((out / "record.json").read_text(encoding="utf-8"))
    assert saved_record["best_version"] is None and saved_record["rounds"][0]["passed"] is False
    assert not (out / "mcp").exists() and not (out / "INSTALL-MCP.txt").exists()


def test_check_and_record_refuse_a_hard_link_to_a_file_outside_the_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    folder = site(tmp_path / "s")
    outside = tmp_path / "secret.txt"
    outside.write_text("private", encoding="utf-8")
    try:
        (folder / "notes.txt").hardlink_to(outside)
    except OSError:
        pytest.skip("this machine does not allow hard links")
    assert record(tmp_path, "site", folder) != 0
    assert "link" in capsys.readouterr().err.lower()
    assert not (tmp_path / "out" / "v1").exists()


@pytest.mark.parametrize("kind", ["rule", "agent"])
def test_record_of_a_file_that_is_not_markdown_is_a_clear_error(tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str) -> None:
    source = tmp_path / "thing.txt"
    source.write_text("Always say please.\n", encoding="utf-8")
    assert record(tmp_path, kind, source) != 0
    assert ".md" in capsys.readouterr().err
    assert not (tmp_path / "out" / "v1").exists()


@needs_ffmpeg
def test_render_video_reports_a_leftover_work_folder_instead_of_crashing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = video_folder(tmp_path)
    (folder / "work").mkdir()
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) == 2
    assert "work" in capsys.readouterr().err


# ---------------------------------------------------------------- found by the second review


def test_record_again_keeps_files_the_user_added_to_the_out_folder(tmp_path: Path) -> None:
    agent = tmp_path / "a.md"
    agent.write_text(AGENT, encoding="utf-8")
    assert record(tmp_path, "agent", agent) == 0
    out = tmp_path / "out"
    (out / "notes.md").write_text("mine", encoding="utf-8")
    agent.write_text(AGENT + "Be brief.\n", encoding="utf-8")
    assert record(tmp_path, "agent", agent) == 0
    assert (out / "notes.md").read_text(encoding="utf-8") == "mine"
    assert "Be brief." in (out / "refund-agent.md").read_text(encoding="utf-8")


def test_record_a_skill_again_keeps_other_skill_folders_in_out(tmp_path: Path) -> None:
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
    assert record(tmp_path, "skill", skill) == 0
    other = tmp_path / "out" / "other-skill"
    other.mkdir()
    (other / "SKILL.md").write_text("keep", encoding="utf-8")
    assert record(tmp_path, "skill", skill) == 0
    assert (other / "SKILL.md").read_text(encoding="utf-8") == "keep"
    assert (tmp_path / "out" / "refund-helper" / "SKILL.md").is_file()


def test_a_delivered_skill_carries_its_support_files(tmp_path: Path) -> None:
    skill = tmp_path / "s"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (skill / "scripts" / "helper.py").write_text("print('hi')\n", encoding="utf-8")
    assert record(tmp_path, "skill", skill) == 0
    assert (tmp_path / "out" / "refund-helper" / "scripts" / "helper.py").read_text(encoding="utf-8") == "print('hi')\n"


def test_record_refuses_to_mix_kinds_in_one_out_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    prompt = tmp_path / "p.md"
    prompt.write_text(_long_prompt("Say hello."), encoding="utf-8")
    assert record(tmp_path, "prompt", prompt, "--score", "9") == 0
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
    assert record(tmp_path, "skill", skill) == 2
    assert "kind" in capsys.readouterr().err
    assert len(saved(tmp_path)["rounds"]) == 1
    assert not (tmp_path / "out" / "v2").exists()


def test_check_site_needs_an_entry_page(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli.main(["check", "site", str(empty)]) == 2
    assert "index.html" in capsys.readouterr().err


@needs_ffmpeg
def test_render_video_refuses_a_mix_of_pictures_and_clips(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = video_folder(tmp_path)
    (folder / "clip.mp4").write_bytes(b"not really a video")
    script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    script["shots"][1]["file"] = "clip.mp4"
    (folder / "script.json").write_text(json.dumps(script), encoding="utf-8")
    assert cli.main(["render", "video", str(folder), "--formats", "1x1", "--size-scale", "0.25"]) == 2
    assert "mix" in capsys.readouterr().err


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


# ---------------------------------------------------------------- the host skill ships with the package

PACKAGED_HOST_SKILL = Path(__file__).resolve().parents[1] / "src" / "proofhouse" / "optimize" / "data" / "proofhouse-host" / "SKILL.md"


def test_the_packaged_host_skill_matches_the_source_skill() -> None:
    assert PACKAGED_HOST_SKILL.is_file(), "run scripts/build_skill_bundle.py"
    assert PACKAGED_HOST_SKILL.read_bytes() == (SKILL_DIR / "SKILL.md").read_bytes().replace(b"\r\n", b"\n")


def test_install_skill_installs_the_host_skill_from_the_package(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dest = tmp_path / "skills"
    assert cli.main(["install-skill", "--skill", "proofhouse-host", "--dest", str(dest)]) == 0
    assert (dest / "proofhouse-host" / "SKILL.md").is_file()
    assert "proofhouse-host" in capsys.readouterr().out


def test_install_skill_without_a_choice_still_installs_proofhouse(tmp_path: Path) -> None:
    dest = tmp_path / "skills"
    assert cli.main(["install-skill", "--dest", str(dest)]) == 0
    assert (dest / "proofhouse" / "SKILL.md").is_file()
    assert not (dest / "proofhouse-host").exists()


def test_install_skill_refuses_a_skill_and_a_bundle_together(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["install-skill", "--skill", "proofhouse-host", "--bundle", str(SKILL_DIR), "--dest", str(tmp_path / "s")])
    assert code != 0
    assert "--skill" in capsys.readouterr().err



# ---------------------------------------------------------------- app, copy and prompt


def pwa(folder: Path, *, worker: bool = True) -> Path:
    wired = SITE.replace(
        "</head>",
        '<link rel="manifest" href="manifest.webmanifest">'
        "<script>navigator.serviceWorker.register('service-worker.js')</script></head>",
    )
    site(folder, wired)
    (folder / "manifest.webmanifest").write_text(json.dumps({
        "name": "Bakery", "start_url": "index.html", "display": "standalone",
        "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"}]}), encoding="utf-8")
    (folder / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8"/></svg>', encoding="utf-8")
    if worker:
        (folder / "service-worker.js").write_text("self.addEventListener('fetch', () => {});\n", encoding="utf-8")
    return folder


def test_check_app_passes_a_working_installable_app(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "app", str(pwa(tmp_path / "app"))]) == 0
    assert "service-worker.js" in capsys.readouterr().out


def test_check_app_fails_when_the_service_worker_is_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "app", str(pwa(tmp_path / "app", worker=False))]) != 0
    assert "service-worker.js" in capsys.readouterr().out


def test_check_app_needs_an_entry_page(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "app").mkdir()
    assert cli.main(["check", "app", str(tmp_path / "app")]) != 0
    assert "index.html" in capsys.readouterr().err


def test_record_app_keeps_every_version_and_delivers_the_best_app(tmp_path: Path) -> None:
    assert record(tmp_path, "app", pwa(tmp_path / "a1", worker=False), "--score", "9") == 0
    assert saved(tmp_path)["best_version"] is None
    assert record(tmp_path, "app", pwa(tmp_path / "a2"), "--score", "7") == 0
    out = tmp_path / "out"
    assert (out / "v1" / "app" / "index.html").is_file() and (out / "v2" / "app" / "manifest.webmanifest").is_file()
    assert (out / "app" / "service-worker.js").is_file()
    assert saved(tmp_path)["best_version"] == 2


def test_record_refuses_an_app_link_that_points_outside_the_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = pwa(tmp_path / "app")
    secret = tmp_path / "secret.txt"
    secret.write_text("private", encoding="utf-8")
    try:
        (folder / "notes.txt").symlink_to(secret)
    except OSError:
        pytest.skip("this machine does not allow symbolic links")
    assert record(tmp_path, "app", folder) != 0
    assert "link" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("kind", ["prompt", "copy"])
def test_check_text_kinds_fail_on_empty_text_and_leftover_filler(tmp_path: Path, kind: str) -> None:
    good, empty, filler = tmp_path / "good.md", tmp_path / "empty.md", tmp_path / "filler.md"
    good.write_text(_long_copy(), encoding="utf-8")
    empty.write_text("  \n", encoding="utf-8")
    filler.write_text("Welcome to [Company Name]. Lorem ipsum dolor.\n", encoding="utf-8")
    assert cli.main(["check", kind, str(good)]) == 0
    assert cli.main(["check", kind, str(empty)]) != 0
    assert cli.main(["check", kind, str(filler)]) != 0


def test_a_prompt_may_keep_its_variables(tmp_path: Path) -> None:
    prompt = tmp_path / "p.md"
    prompt.write_text(_long_prompt("Summarise {{article}} in {{words}} words."), encoding="utf-8")
    assert cli.main(["check", "prompt", str(prompt)]) == 0


def test_record_copy_delivers_final_md_and_keeps_versions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    first, second = tmp_path / "c1.md", tmp_path / "c2.md"
    first.write_text(_long_copy().replace("\n", " TODO better headline.\n"), encoding="utf-8")
    second.write_text("# Bread by 5 AM\n" + _long_copy(), encoding="utf-8")
    assert record(tmp_path, "copy", first, "--score", "9") == 0
    assert saved(tmp_path)["best_version"] is None and not (tmp_path / "out" / "final.md").exists()
    assert record(tmp_path, "copy", second, "--score", "7") == 0
    assert (tmp_path / "out" / "final.md").read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert saved(tmp_path)["best_version"] == 2


@pytest.mark.skipif(os.name != "nt", reason="Windows drive names")
def test_clear_delivery_ignores_a_drive_name(tmp_path: Path) -> None:
    out = tmp_path / "out"
    (out / "v1").mkdir(parents=True)
    (out / "v1" / "keep.txt").write_text("x", encoding="utf-8")
    host._clear_delivery(out, [out.drive, "C:", "D:"])
    assert (out / "v1" / "keep.txt").exists()


def test_check_site_browser_that_exits_with_an_error_is_not_a_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import sitecheck

    fake = tmp_path / "chrome.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(fake))

    def record_launch(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=2, stdout="", stderr="unknown option --headless")

    monkeypatch.setattr(sitecheck, "_open", record_launch)
    rows = {c["check"]: c for c in sitecheck.check_site(site(tmp_path / "s"))}
    assert "no JavaScript errors in the browser" not in rows
    assert rows["opened in a browser"]["ok"] is None
    assert "code 2" in rows["opened in a browser"]["detail"]
