"""Offline make checks for rules, stdio MCP servers, and command hooks."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from proofhouse import cli, live, make, make_checks
from proofhouse.live_cli import EXIT_REFUSED


class ScriptedModel:
    def __init__(self, replies: list[dict[str, object] | str], scores: list[int] | None = None) -> None:
        self.replies = list(replies)
        self.scores = list(scores or [9] * len(replies))
        self.judged: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        prompt = " ".join(message["content"] for message in json.loads(request.body_bytes)["messages"])
        if prompt.startswith("You judge AI work"):
            self.judged.append(prompt)
            content = json.dumps({"score": self.scores.pop(0), "missing": [], "fix": "fix checks"})
        else:
            reply = self.replies.pop(0)
            content = reply if isinstance(reply, str) else json.dumps(reply)
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


def made(tmp_path: Path, kind: str, model: ScriptedModel, rounds: int = 1, allow: bool = True) -> Path:
    make.make(f"a useful {kind}", provider_id="ollama", model="m", kind=kind, rounds=rounds,
              out_dir=tmp_path / "out", transport=model, allow_commands=allow)
    return tmp_path / "out"


def checks(folder: Path, version: int = 1) -> list[dict[str, object]]:
    return json.loads((folder / f"v{version}" / "checks.json").read_text(encoding="utf-8"))


def test_rule_round_trips_every_rule_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "outside-home"))
    model = ScriptedModel([{"name": "safe-edits", "content": "# Safe edits\nRead before changing files."}])
    folder = made(tmp_path, "rule", model)
    results = checks(folder)
    assert {row["host"] for row in results} == {"claude", "cursor", "codex"}
    assert all(row["ok"] is True and row["detail"] == "restored exactly" for row in results)
    assert (folder / "safe-edits.md").read_text(encoding="utf-8").startswith("# Safe edits")
    assert not (tmp_path / "outside-home").exists()
    assert "PASS:" in model.judged[0]


SERVER = """import json, os, sys
for line in sys.stdin:
    request = json.loads(line)
    if request.get('method') == 'initialize':
        result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'tiny', 'version': '1'}}
    elif request.get('method') == 'tools/list':
        result = {'tools': [] if os.environ.get('FAKE_SECRET_KEY') else [{'name': 'echo', 'inputSchema': {'type': 'object'}}]}
    else:
        continue
    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)
"""


def test_mcp_process_lists_tools_without_parent_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_SECRET_KEY", "do-not-pass")
    model = ScriptedModel([{"name": "tiny-server", "command": "python", "args": ["server.py"],
                            "files": {"server.py": SERVER}}])
    folder = made(tmp_path, "mcp", model)
    assert checks(folder)[0]["ok"] is True
    assert "PASS: MCP tools/list" in model.judged[0]
    assert (folder / "mcp" / "server.py").is_file()
    install = (folder / "INSTALL-MCP.txt").read_text(encoding="utf-8")
    assert "proofhouse install mcp tiny-server --command=python" in install
    assert '--arg="<this-folder>/mcp/server.py"' in install
    assert "Replace <this-folder>" in install
    assert str(tmp_path) not in install and tmp_path.as_posix() not in install


@pytest.mark.parametrize("command,server,expected", [
    ("python", SERVER.replace("[{'name': 'echo', 'inputSchema': {'type': 'object'}}]", "[]"), False),
    ("proofhouse-command-that-does-not-exist", SERVER, None),
])
def test_mcp_no_tools_fails_and_missing_command_is_unchecked(
    tmp_path: Path, command: str, server: str, expected: bool | None,
) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "tiny", "command": command, "args": ["server.py"],
                                                    "files": {"server.py": server}}]))
    assert checks(folder)[0]["ok"] is expected
    if expected is None:
        assert checks(folder)[0]["detail"] == f"not checked: {command} not found"


def test_a_check_that_was_not_run_is_counted_as_not_run_and_says_how_to_run_it(tmp_path: Path) -> None:
    reply = {"name": "tiny-server", "command": "python", "args": ["server.py"], "files": {"server.py": SERVER}}
    summary, subject = make._try_new_kind("mcp", json.dumps(reply), "an mcp server", tmp_path / "v1", allow_commands=False)
    assert summary == "0 of 1 checks passed, 1 not run (add --allow-commands to run them)"
    assert "NOT CHECKED: MCP tools/list" in subject
    summary, _ = make._try_new_kind("mcp", json.dumps(reply), "an mcp server", tmp_path / "v2", allow_commands=True)
    assert summary == "1 of 1 checks passed"


def test_hook_runs_known_event_without_parent_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_SECRET_KEY", "do-not-pass")
    script = "import json, os, sys\nevent = json.load(sys.stdin)\nprint(event['hook_event_name'])\nprint('blocked: demo', file=sys.stderr)\nsys.exit(1 if 'FAKE_SECRET_KEY' in os.environ else 2)\n"
    model = ScriptedModel([{"event": "PreToolUse", "matcher": "Bash", "command": "python hook.py",
                            "files": {"hook.py": script}, "sample_event": {"hook_event_name": "PreToolUse"}}])
    folder = made(tmp_path, "hook", model)
    result = checks(folder)[0]
    assert result["ok"] is True and result["exit_code"] == 2 and result["stdout"].strip() == "PreToolUse"
    snippet = json.loads((folder / "settings-snippet.json").read_text(encoding="utf-8"))
    assert snippet["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert snippet["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == 'python "<this-folder>/hook/hook.py"'
    assert str(tmp_path) not in json.dumps(snippet) and tmp_path.as_posix() not in json.dumps(snippet)
    assert "Replace <this-folder>" in (folder / "INSTALL-HOOK.txt").read_text(encoding="utf-8")
    assert "PASS: hook execution" in model.judged[0]


def test_unknown_hook_event_fails(tmp_path: Path) -> None:
    folder = made(tmp_path, "hook", ScriptedModel([{"event": "NotAnEvent", "command": "python hook.py",
                                                     "files": {"hook.py": "pass"}, "sample_event": {}}]))
    assert checks(folder)[0]["ok"] is False
    assert "unknown event" in str(checks(folder)[0]["detail"])


CHILD = "import pathlib, time\nwhile True:\n    pathlib.Path('beat.txt').write_text(str(time.time()))\n    time.sleep(0.1)\n"
PARENT = "import subprocess, sys, time\nsubprocess.Popen([sys.executable, 'child.py'])\ntime.sleep(60)\n"


def test_hanging_hook_is_killed_with_its_children(tmp_path: Path) -> None:
    folder = made(tmp_path, "hook", ScriptedModel([{"event": "Stop", "command": "python hook.py",
                                                     "files": {"hook.py": PARENT, "child.py": CHILD},
                                                     "sample_event": {"hook_event_name": "Stop"}}]))
    assert checks(folder)[0]["ok"] is False
    assert "timed out" in str(checks(folder)[0]["detail"])
    beat = folder / "v1" / "hook" / "beat.txt"
    assert beat.is_file()
    before = beat.read_text(encoding="utf-8")
    time.sleep(1)
    assert beat.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("name", ["../outside.py", "/outside.py", "dir/../../outside.py", "C:/outside.py"])
def test_generated_files_cannot_escape_version_folder(tmp_path: Path, name: str) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "bad", "command": "python", "args": [],
                                                    "files": {name: "bad"}}]))
    assert checks(folder)[0]["ok"] is False
    assert "unsafe file name" in str(checks(folder)[0]["detail"])
    assert not list(tmp_path.rglob("outside.py"))


MARKER = "import pathlib\npathlib.Path('started.txt').write_text('ran')\n"


def test_without_opt_in_nothing_is_started(tmp_path: Path) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "tiny", "command": "python", "args": ["server.py"],
                                                    "files": {"server.py": MARKER + SERVER}}]), allow=False)
    result = checks(folder)[0]
    assert result["ok"] is None and "--allow-commands" in str(result["detail"])
    assert not (folder / "v1" / "mcp" / "started.txt").exists()
    hook_folder = made(tmp_path / "h", "hook", ScriptedModel([{"event": "Stop", "command": "python hook.py",
                                                               "files": {"hook.py": MARKER},
                                                               "sample_event": {"hook_event_name": "Stop"}}]), allow=False)
    assert checks(hook_folder)[0]["ok"] is None
    assert not (hook_folder / "v1" / "hook" / "started.txt").exists()


def test_with_opt_in_the_hook_runs_and_its_output_is_not_delivered(tmp_path: Path) -> None:
    folder = made(tmp_path, "hook", ScriptedModel([{"event": "Stop", "command": "python hook.py",
                                                     "files": {"hook.py": MARKER},
                                                     "sample_event": {"hook_event_name": "Stop"}}]))
    assert checks(folder)[0]["ok"] is True
    assert (folder / "v1" / "hook" / "started.txt").is_file()
    assert (folder / "hook" / "hook.py").is_file()
    assert not (folder / "hook" / "started.txt").exists()


@pytest.mark.parametrize("command,args", [
    ("python;calc", ["server.py"]),
    ("python", ["server.py", "&&", "calc"]),
    ("python", ["server.py\ncalc"]),
    ("python", ["$(calc)"]),
    ("python", ['server.py"', "x"]),
    ("./../outside", []),
    ("py thon", ["server.py"]),
    ("python", ["/etc/hosts"]),
    ("python", ["C:/Windows/win.ini"]),
    ("-python", ["server.py"]),
])
def test_mcp_shell_characters_are_refused(tmp_path: Path, command: str, args: list[str]) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "tiny", "command": command, "args": args,
                                                    "files": {"server.py": MARKER + SERVER}}]))
    result = checks(folder)[0]
    assert result["ok"] is False and "unsafe" in str(result["detail"])
    assert not (folder / "v1" / "mcp" / "started.txt").exists()
    assert not (folder / "INSTALL-MCP.txt").exists()


@pytest.mark.parametrize("command", ["python hook.py | calc", "python hook.py; calc", "python hook.py `calc`",
                                     "python hook.py > out.txt", "python ../hook.py"])
def test_hook_shell_characters_are_refused(tmp_path: Path, command: str) -> None:
    folder = made(tmp_path, "hook", ScriptedModel([{"event": "Stop", "command": command, "files": {"hook.py": MARKER},
                                                     "sample_event": {"hook_event_name": "Stop"}}]))
    assert checks(folder)[0]["ok"] is False
    assert not (folder / "v1" / "hook" / "started.txt").exists()
    assert not (folder / "settings-snippet.json").exists()


def test_blocking_hook_must_give_a_reason(tmp_path: Path) -> None:
    folder = made(tmp_path, "hook", ScriptedModel([{"event": "Stop", "command": "python hook.py",
                                                     "files": {"hook.py": "import sys\nsys.exit(2)\n"},
                                                     "sample_event": {"hook_event_name": "Stop"}}]))
    result = checks(folder)[0]
    assert result["ok"] is False and "no reason" in str(result["detail"])


def test_hook_naming_a_missing_script_fails(tmp_path: Path) -> None:
    folder = made(tmp_path, "hook", ScriptedModel([{"event": "Stop", "command": "python missing.py",
                                                     "files": {"hook.py": "pass\n"},
                                                     "sample_event": {"hook_event_name": "Stop"}}]))
    result = checks(folder)[0]
    assert result["ok"] is False and "missing.py" in str(result["detail"])


def test_mcp_local_command_that_was_not_written_fails(tmp_path: Path) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "tiny", "command": "./server", "args": [],
                                                    "files": {"server.py": SERVER}}]))
    result = checks(folder)[0]
    assert result["ok"] is False and "not written" in str(result["detail"])


@pytest.mark.parametrize("name", ["nul", "con.py", "lib/aux.txt", "COM1.js", "lib./x.py", "x.py."])
def test_device_and_trailing_dot_names_are_refused(tmp_path: Path, name: str) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "bad", "command": "python", "args": [],
                                                    "files": {name: "bad"}}]))
    result = checks(folder)[0]
    assert result["ok"] is False and "unsafe file name" in str(result["detail"])


def test_delivered_lines_name_the_program_that_was_checked(tmp_path: Path) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "tiny", "command": "python", "args": ["server.py"],
                                                    "files": {"python": "not a program", "server.py": SERVER}}]))
    assert "Proofhouse's own Python" in str(checks(folder)[0]["detail"])
    assert "--command=python --arg=" in (folder / "INSTALL-MCP.txt").read_text(encoding="utf-8")
    hook_folder = made(tmp_path / "h", "hook", ScriptedModel([{"event": "Stop", "command": "python hook.py",
                                                               "files": {"python": "not a program", "hook.py": "pass\n"},
                                                               "sample_event": {"hook_event_name": "Stop"}}]))
    snippet = json.loads((hook_folder / "settings-snippet.json").read_text(encoding="utf-8"))
    assert snippet["hooks"]["Stop"][0]["hooks"][0]["command"].startswith("python ")


def test_rule_with_a_bad_name_fails(tmp_path: Path) -> None:
    folder = made(tmp_path, "rule", ScriptedModel([{"name": "Bad Name", "content": "# Rule"}]))
    result = checks(folder)[0]
    assert result["ok"] is False and "lowercase" in str(result["detail"])


def test_mcp_with_a_bad_name_fails(tmp_path: Path) -> None:
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "Bad Name", "command": "python", "args": ["server.py"],
                                                    "files": {"server.py": MARKER + SERVER}}]))
    assert checks(folder)[0]["ok"] is False
    assert not (folder / "v1" / "mcp" / "started.txt").exists()


def test_mcp_with_one_broken_tool_fails(tmp_path: Path) -> None:
    server = SERVER.replace("[{'name': 'echo', 'inputSchema': {'type': 'object'}}]",
                            "[{'name': 'echo', 'inputSchema': {'type': 'object'}}, {'name': ''}]")
    folder = made(tmp_path, "mcp", ScriptedModel([{"name": "tiny", "command": "python", "args": ["server.py"],
                                                    "files": {"server.py": server}}]))
    assert checks(folder)[0]["ok"] is False


def test_settings_snippet_refuses_unknown_events(tmp_path: Path) -> None:
    assert make_checks.settings_snippet("NotAnEvent", None, "python hook.py", tmp_path) is None
    assert make_checks.settings_snippet("Stop", None, "python hook.py", tmp_path) is not None


def test_unwritten_mcp_is_not_reported_as_made(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    # A local model returned prose instead of the JSON spec: the judge still scored it 8, but nothing was written.
    monkeypatch.setattr(live, "_httpx_post", ScriptedModel(["Here is your server: it returns the time."], [8]))
    code = cli.main(["make", "an MCP server that returns the time", "--kind", "mcp", "--provider", "ollama",
                     "--model", "m", "--rounds", "1", "--out", str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert checks(tmp_path / "out")[0] == {"check": "mcp written", "ok": False,
                                            "detail": checks(tmp_path / "out")[0]["detail"]}
    assert code == EXIT_REFUSED
    assert "made: nothing usable" in out and "server:" not in out
    assert not (tmp_path / "out" / "mcp").exists() and not (tmp_path / "out" / "INSTALL-MCP.txt").exists()
    record = json.loads((tmp_path / "out" / "record.json").read_text(encoding="utf-8"))
    assert record["best_version"] is None


def test_best_version_is_one_that_was_written(tmp_path: Path) -> None:
    model = ScriptedModel([{"name": "tiny-server", "command": "python", "args": ["server.py"], "files": {"server.py": SERVER}},
                           "not json at all"], [5, 9])
    result = make.make("a useful mcp", provider_id="ollama", model="m", kind="mcp", rounds=2, target=10,
                       out_dir=tmp_path / "out", transport=model, allow_commands=True)
    assert result.best_version == 1 and result.best_score == 5
    assert (tmp_path / "out" / "mcp" / "server.py").is_file()


def test_made_line_says_how_many_checks_passed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(live, "_httpx_post", ScriptedModel(
        [{"name": "tiny-server", "command": "python", "args": ["server.py"], "files": {"server.py": SERVER}}]))
    code = cli.main(["make", "a useful mcp", "--kind", "mcp", "--provider", "ollama", "--model", "m", "--rounds", "1",
                     "--allow-commands", "--out", str(tmp_path / "out")])
    assert code == 0 and "made: version 1 (judge score 9/10; 1 of 1 checks passed)" in capsys.readouterr().out


def test_hook_writer_is_told_every_event_name_it_may_use(tmp_path: Path) -> None:
    seen: list[str] = []
    inner = ScriptedModel([{"event": "PreToolUse", "command": "python hook.py",
                            "files": {"hook.py": "import sys\nsys.exit(0)\n"},
                            "sample_event": {"hook_event_name": "PreToolUse"}}])

    def spy(request: live.Request) -> live.Response:
        seen.append(" ".join(message["content"] for message in json.loads(request.body_bytes)["messages"]))
        return inner(request)

    make.make("block commits that contain API keys", provider_id="ollama", model="m", kind="hook", rounds=1,
              out_dir=tmp_path / "out", transport=spy, allow_commands=True)
    for event in make_checks._known_events():
        assert event in seen[0]
    assert "git hook" in seen[0]
