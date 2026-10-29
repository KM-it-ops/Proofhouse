"""`proofhouse setup`: find what this machine has, say what is missing and what it unlocks, take tools the user declares."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from proofhouse import cli, providers, setup_check


class FakeProbe:
    """A machine we describe: which programs exist, which keys are set, which local servers answer."""

    def __init__(self, programs: tuple[str, ...] = (), keys: tuple[str, ...] = (), servers: tuple[int, ...] = (),
                 system: tuple[str, str] = ("Windows", "AMD64"), modules: tuple[str, ...] = (), browser: str | None = None) -> None:
        self.programs, self.keys, self.servers, self.system, self.modules, self.chosen_browser = programs, keys, servers, system, modules, browser

    def which(self, name: str) -> str | None:
        return f"/fake/bin/{name}" if name in self.programs else None

    def key_is_set(self, name: str) -> bool:
        return name in self.keys

    def answers(self, host: str, port: int) -> bool:
        return port in self.servers

    def platform(self) -> tuple[str, str]:
        return self.system

    def has_module(self, name: str) -> bool:
        return name in self.modules

    def browser(self) -> str | None:
        return self.chosen_browser


def _abilities(report: setup_check.Report) -> dict[str, setup_check.Ability]:
    return {a.id: a for a in report.abilities}


def test_a_bare_machine_can_still_check_and_record_and_is_told_what_each_missing_piece_unlocks() -> None:
    report = setup_check.build_report(FakeProbe())
    can = _abilities(report)
    assert can["host-check"].ok  # needs nothing
    assert not can["render-video"].ok and "ffmpeg" in can["render-video"].get
    assert not can["make-with-model"].ok and "key" in can["make-with-model"].get.lower()
    assert not can["open-sites"].ok and "Chrome" in can["open-sites"].get
    assert not can["deploy-site"].ok
    assert not can["write-with-agent"].ok
    text = setup_check.render(report)
    assert "You can" in text and "Not yet" in text
    assert "ffmpeg" in text and "unlocks" in text.lower()


def test_agents_on_the_machine_are_found_and_unlock_host_mode() -> None:
    report = setup_check.build_report(FakeProbe(programs=("claude", "codex")))
    found = {t.id for t in report.tools if t.found}
    assert {"claude", "codex"} <= found and "gemini" not in found
    assert _abilities(report)["write-with-agent"].ok


def test_a_key_is_reported_as_set_or_not_set_and_its_value_never_appears(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-SECRET-VALUE-123")
    from proofhouse.setup_check import SystemProbe

    report = setup_check.build_report(SystemProbe())
    by_env = {k.env: k for k in report.keys}
    assert by_env["OPENAI_API_KEY"].is_set and not by_env["MISTRAL_API_KEY"].is_set
    assert "openai" in by_env["OPENAI_API_KEY"].used_by
    assert _abilities(report)["make-with-model"].ok
    assert "sk-SECRET" not in setup_check.render(report)
    assert "sk-SECRET" not in json.dumps(report.to_dict())


def test_a_local_model_server_that_answers_is_found_and_one_that_does_not_is_not() -> None:
    report = setup_check.build_report(FakeProbe(servers=(11434,)))
    local = {s.id: s.answering for s in report.servers}
    assert local["ollama"] and not local["lmstudio"]
    assert _abilities(report)["make-with-model"].ok
    assert _abilities(report)["free-local-model"].ok


def test_an_installed_but_not_running_server_says_to_start_it() -> None:
    report = setup_check.build_report(FakeProbe(programs=("ollama",)))
    ollama = next(s for s in report.servers if s.id == "ollama")
    assert ollama.installed and not ollama.answering
    assert "start" in setup_check.render(report).lower()
    assert not _abilities(report)["make-with-model"].ok


def test_a_hosting_tool_unlocks_publishing_and_the_report_says_sign_in_is_not_checked() -> None:
    report = setup_check.build_report(FakeProbe(programs=("vercel",)))
    assert _abilities(report)["deploy-site"].ok
    assert "sign" in _abilities(report)["deploy-site"].note.lower()


def test_ffmpeg_needs_both_programs_for_video() -> None:
    assert not _abilities(setup_check.build_report(FakeProbe(programs=("ffmpeg",))))["render-video"].ok
    assert _abilities(setup_check.build_report(FakeProbe(programs=("ffmpeg", "ffprobe"))))["render-video"].ok


def test_a_browser_unlocks_opening_sites() -> None:
    assert _abilities(setup_check.build_report(FakeProbe(browser="/x/chrome")))["open-sites"].ok


def test_training_needs_apple_silicon_with_mlx_or_a_training_service_key() -> None:
    assert not _abilities(setup_check.build_report(FakeProbe()))["train-model"].ok
    mac = FakeProbe(system=("Darwin", "arm64"), modules=("mlx_lm",))
    assert _abilities(setup_check.build_report(mac))["train-model"].ok
    assert _abilities(setup_check.build_report(FakeProbe(keys=("TOGETHER_API_KEY",))))["train-model"].ok


def test_media_keys_unlock_media() -> None:
    assert not _abilities(setup_check.build_report(FakeProbe()))["make-media"].ok
    assert _abilities(setup_check.build_report(FakeProbe(keys=("OPENAI_API_KEY",))))["make-media"].ok


def test_a_declared_command_line_tool_is_found_when_it_is_on_the_machine() -> None:
    setup_check.add_tool(id="mygen", name="My generator", how="cli", command="mygen", makes=("image",))
    found = setup_check.build_report(FakeProbe(programs=("mygen",)))
    mine = next(t for t in found.declared if t.id == "mygen")
    assert mine.found and mine.how == "cli"
    assert _abilities(found)["make-media"].ok
    missing = setup_check.build_report(FakeProbe())
    assert not next(t for t in missing.declared if t.id == "mygen").found
    assert not _abilities(missing)["make-media"].ok


def test_a_declared_website_tool_is_recorded_as_hand_driven_with_its_steps_and_where_the_file_goes_back() -> None:
    setup_check.add_tool(id="supergrok", name="Grok Imagine", how="web", url="https://grok.com/imagine", makes=("image", "video"),
                         steps=("Open the page in Chrome", "Paste the brief", "Download the file"))
    report = setup_check.build_report(FakeProbe())
    tool = next(t for t in report.declared if t.id == "supergrok")
    assert tool.how == "web" and tool.hand_driven and not tool.found
    assert _abilities(report)["make-media"].ok  # a person can drive it
    text = setup_check.render(report)
    assert "Open the page in Chrome" in text and "proofhouse record" in text and "render video" in text
    assert "by hand" in text


def test_declaring_checks_its_input_and_changes_nothing_when_it_is_wrong() -> None:
    for bad in (
        dict(id="Bad Id", name="x", how="cli", command="x"),
        dict(id="ok", name="x", how="telepathy", command="x"),
        dict(id="ok", name="x", how="cli"),
        dict(id="ok", name="x", how="web"),
        dict(id="ok", name="x", how="cli", command="x", makes=("smell",)),
        dict(id="ok", name="", how="cli", command="x"),
    ):
        with pytest.raises(setup_check.SetupError):
            setup_check.add_tool(**bad)  # type: ignore[arg-type]
    assert not setup_check.user_path().exists()


def test_a_tool_can_be_replaced_and_removed() -> None:
    setup_check.add_tool(id="mygen", name="One", how="cli", command="mygen")
    setup_check.add_tool(id="mygen", name="Two", how="cli", command="mygen")
    assert [t["name"] for t in setup_check.load_user()["tools"]] == ["Two"]
    setup_check.remove_tool("mygen")
    assert setup_check.load_user()["tools"] == []
    with pytest.raises(setup_check.SetupError, match="no declared tool"):
        setup_check.remove_tool("mygen")


def test_a_broken_tools_file_is_refused_with_a_plain_message_and_not_overwritten() -> None:
    path = setup_check.user_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(setup_check.SetupError, match="unreadable"):
        setup_check.build_report(FakeProbe())
    with pytest.raises(setup_check.SetupError):
        setup_check.add_tool(id="a", name="A", how="cli", command="a")
    assert path.read_text(encoding="utf-8") == "{not json"


def test_looking_never_starts_a_program_or_opens_a_network_connection_beyond_this_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("setup must not start a program")

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    seen: list[str] = []
    import socket

    real = socket.create_connection

    def watch(address: tuple[str, int], *args: object, **kwargs: object):
        seen.append(address[0])
        return real(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", watch)
    setup_check.build_report(setup_check.SystemProbe())
    assert set(seen) <= {"localhost", "127.0.0.1", "::1"}


def test_the_command_prints_a_plain_report_and_exits_zero(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_check, "SystemProbe", lambda: FakeProbe(programs=("claude", "ffmpeg", "ffprobe")))
    assert cli.main(["setup"]) == 0
    out = capsys.readouterr().out
    assert "Claude Code" in out and "You can" in out and "Not yet" in out and "proofhouse" in out


def test_the_command_has_a_json_form(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_check, "SystemProbe", lambda: FakeProbe(keys=("OPENAI_API_KEY",)))
    assert cli.main(["setup", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"tools", "keys", "servers", "declared", "abilities"} <= set(data)
    assert any(k["env"] == "OPENAI_API_KEY" and k["set"] for k in data["keys"])


def test_add_and_remove_through_the_command(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_check, "SystemProbe", lambda: FakeProbe())
    assert cli.main(["setup", "add", "grok-imagine", "--name", "Grok Imagine", "--how", "web", "--url", "https://grok.com/imagine",
                     "--makes", "image,video", "--step", "Open the page", "--step", "Download the clip"]) == 0
    assert "grok-imagine" in capsys.readouterr().out
    assert cli.main(["setup"]) == 0
    out = capsys.readouterr().out
    assert "Grok Imagine" in out and "Download the clip" in out
    assert cli.main(["setup", "remove", "grok-imagine"]) == 0
    capsys.readouterr()
    assert cli.main(["setup", "remove", "grok-imagine"]) == 2
    assert "no declared tool" in capsys.readouterr().err


def test_a_bad_declaration_through_the_command_is_one_plain_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["setup", "add", "x", "--name", "X", "--how", "cli"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "command" in err and "Traceback" not in err


def test_setup_is_in_the_command_map() -> None:
    from proofhouse.command_map import COMMAND_MAP

    assert {"setup add", "setup remove"} <= set(COMMAND_MAP)  # the bare `setup` is a group, so only its leaves are mapped


def test_the_user_file_lives_next_to_the_other_settings_files() -> None:
    assert setup_check.user_path() == providers.proofhouse_home() / "tools.json"
