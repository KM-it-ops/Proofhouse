"""A newcomer's first look: a start screen, a whole make replayed with no key, and a missing key that says what to type."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

from proofhouse import cli, command_map, demo_make, live


def test_a_bare_proofhouse_shows_where_to_start(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "proofhouse demo make" in out and "proofhouse setup" in out and "proofhouse make" in out
    assert "usage:" not in out
    # every command the start screen names is a real one
    for line in out.splitlines():
        if line.startswith("  proofhouse "):
            name = line.split()[1]  # a group such as `setup` is mapped by its leaves
            assert any(key == name or key.startswith(name + " ") for key in command_map.COMMAND_MAP), line


def test_demo_make_replays_a_whole_make_with_no_key_and_no_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                    capsys: pytest.CaptureFixture[str]) -> None:
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("the replay must not reach the network")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(live, "_send", no_network, raising=False)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert cli.main(["demo", "make", "--workspace", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("This is a replay.")  # a replay never passes for a live run
    assert "[must know]" in out  # the ranked questions are asked
    assert "You left the length to me. I chose:" in out  # a blank answer comes back as a stated choice
    assert out.count("Here is what I understood:") == 2  # the correction is said back before anything is made
    assert "version 1: judge score 7/10, 5 of 6 asked-for items met" in out
    assert "not met: One line per change, 20 lines at most" in out
    assert "version 2: judge score 9/10, 6 of 6 asked-for items met" in out
    assert "asked for: 6 of 6 met" in out and "advice, not proof" in out
    # it is the real make: the same record a live make leaves, and the skill itself
    record = json.loads((tmp_path / "make" / "record.json").read_text(encoding="utf-8"))
    assert len(record["asked_for"]) == 6 and len(record["rounds"]) == 2
    skills = list((tmp_path / "make").rglob("SKILL.md"))
    assert skills and "20 lines at most" in skills[-1].read_text(encoding="utf-8")


def test_the_recording_follows_the_interview_it_replays() -> None:
    data = demo_make.recording()
    asked = sum(len(group["questions"]) for group in data["questions"])
    assert len(data["typed"]) == asked + len(data["say_back"])  # one line per question, one per say-back
    assert [a["item"] for a in data["judge"][0]["asked"]] == [a["item"] for a in data["judge"][1]["asked"]]


def test_plain_demo_is_still_the_reference_workflow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["demo", "--workspace", str(tmp_path), "--quiet"]) == 0
    assert "This is a replay." not in capsys.readouterr().out


def test_a_missing_key_says_what_to_type_in_each_shell_and_names_the_free_way(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    refused = live.run_prompt("openai", "gpt-x", prompt="hello", max_cost_usd="1",
                              transport=lambda request: pytest.fail("sent"))
    assert refused.code == "PHC-RUN-0003"
    name, placeholder = "OPENAI_API_KEY", '"your-key"'
    assert f"$env:{name} = {placeholder}" in refused.message  # PowerShell
    assert f"export {name}={placeholder}" in refused.message  # bash
    assert "--provider ollama" in refused.message and "proofhouse setup" in refused.message
