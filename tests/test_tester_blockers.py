"""First-run dead ends a new tester hits with the agent or setup he already has: each says what to do next."""
from __future__ import annotations

from pathlib import Path

import pytest

from proofhouse import cli, host, live


def test_checking_a_prompt_given_a_folder_says_a_file_is_expected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", "prompt", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "folder" in err and "file" in err and str(tmp_path) in err


def test_checking_a_prompt_that_is_not_there_says_it_was_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.md"
    assert cli.main(["check", "prompt", str(missing)]) == 2
    err = capsys.readouterr().err
    assert "not found" in err and str(missing) in err


def test_a_judge_label_is_not_called_a_different_agent_unless_it_is_known_to_be() -> None:
    note = host.judge_note_for_record("claude", "self, same writer")
    assert "different agent" not in note
    assert "self, same writer" in note and "claude" in note and "not proof" in note


def test_an_unknown_agent_for_install_skill_is_told_to_pass_its_skills_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["install-skill", "--host", "gemini"]) == 2
    err = capsys.readouterr().err
    assert "--dest" in err and "skills folder" in err
    assert "invalid choice" in err


def test_install_skill_with_no_agent_named_points_at_dest_for_any_other_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert cli.main(["install-skill"]) == 2
    err = capsys.readouterr().err
    assert "--dest" in err and "any other agent" in err


def test_a_local_model_server_that_is_not_running_says_where_it_looked_and_how_to_start_it() -> None:
    def refused(request: live.Request) -> live.Response:
        raise ConnectionRefusedError("refused")

    result = live.run_prompt("ollama", "llama3", prompt="hi", transport=refused)
    assert result.status == "error"
    assert "localhost:11434" in result.message
    assert "not running" in result.message and "proofhouse setup" in result.message
    assert "ConnectionRefusedError" not in result.message


def test_a_url_error_from_the_standard_library_is_read_the_same_way() -> None:
    import urllib.error

    def refused(request: live.Request) -> live.Response:
        raise urllib.error.URLError("no route")

    result = live.run_prompt("lmstudio", "m", prompt="hi", transport=refused)
    assert "not running" in result.message and "proofhouse setup" in result.message


def test_a_cloud_provider_that_cannot_be_reached_does_not_claim_a_local_server_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder-not-a-key")

    def refused(request: live.Request) -> live.Response:
        raise ConnectionRefusedError("refused")

    result = live.run_prompt("openai", "some-model", prompt="hi", max_cost_usd="0.01", transport=refused)
    assert "not running" not in result.message


@pytest.mark.parametrize("kind", ["agent", "rule"])
def test_checking_an_agent_or_rule_given_a_folder_says_a_file_is_expected(kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check", kind, str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "folder" in err and "file" in err and str(tmp_path) in err


@pytest.mark.parametrize("kind", ["agent", "rule"])
def test_checking_an_agent_or_rule_that_is_not_there_says_it_was_not_found(kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.md"
    assert cli.main(["check", kind, str(missing)]) == 2
    assert "not found" in capsys.readouterr().err
