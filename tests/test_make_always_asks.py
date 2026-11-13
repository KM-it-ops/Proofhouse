"""Every run asks: with no terminal and no --for, a make (or a launch) pauses with its questions instead of making blind."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import cli, launch, live, live_cli, make
from proofhouse.optimize import cli as optimize_cli

from test_make_interview import Owner


@pytest.fixture(autouse=True)
def _no_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(optimize_cli, "_stdin_is_terminal", lambda: False)


def _route(monkeypatch: pytest.MonkeyPatch, model: Owner) -> None:
    real = make.make
    monkeypatch.setattr(make, "make", lambda *a, **k: real(*a, **{**k, "transport": model}))


BASE = ["make", "a skill for refunds", "--kind", "skill", "--provider", "ollama", "--model", "m"]


def test_a_run_with_no_terminal_and_no_for_pauses_and_asks_which_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                      capsys: pytest.CaptureFixture[str]) -> None:
    model = Owner([9])
    _route(monkeypatch, model)
    folder = tmp_path / "o"
    code = cli.main([*BASE, "--out", str(folder)])
    out, err = capsys.readouterr()
    assert code == live_cli.EXIT_WAITING != live_cli.EXIT_OK
    assert "waiting for your answers" in out and f"--answers {folder / 'answers.json'}" in out
    assert "tip: pass --for" not in err
    assert model.calls == []  # nothing made blind, not even the questions before the tool is known
    assert "Which AI tool or model is this for?" in (folder / "questions.md").read_text(encoding="utf-8")
    assert json.loads((folder / "answers.json").read_text(encoding="utf-8"))["for"] == ""
    assert not (folder / "record.json").exists() and not (folder / "v1").exists()


def test_the_paused_run_goes_on_from_the_answers_file_and_the_record_says_so(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    model = Owner([9])
    _route(monkeypatch, model)
    folder = tmp_path / "o"
    answers = folder / "answers.json"
    assert cli.main([*BASE, "--out", str(folder)]) == live_cli.EXIT_WAITING
    filled = json.loads(answers.read_text(encoding="utf-8"))
    answers.write_text(json.dumps({**filled, "for": "Claude Code"}), encoding="utf-8")
    assert cli.main([*BASE, "--answers", str(answers)]) == live_cli.EXIT_WAITING  # now the questions
    assert "**must**" in (folder / "questions.md").read_text(encoding="utf-8")
    filled = json.loads(answers.read_text(encoding="utf-8"))
    filled["answers"]["must"], filled["confirmed"] = "check the order", True
    answers.write_text(json.dumps(filled), encoding="utf-8")
    capsys.readouterr()
    assert cli.main([*BASE, "--answers", str(answers)]) == live_cli.EXIT_OK
    record = json.loads((folder / "record.json").read_text(encoding="utf-8"))
    assert record["interview"]["target"]["id"] == "claude"
    assert record["interview_from"] == "answers file"


def test_answers_given_ahead_make_it_in_one_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = Owner([9])
    _route(monkeypatch, model)
    ahead = tmp_path / "ahead.json"
    ahead.write_text(json.dumps({"for": "Claude Code", "answers": {"must": "check the order"}, "confirmed": True}),
                     encoding="utf-8")
    assert cli.main([*BASE, "--answers", str(ahead), "--preset", "efficient", "--out", str(tmp_path / "o")]) == live_cli.EXIT_OK
    assert "write" in model.calls
    assert json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))["interview_from"] == "answers file"


def test_the_record_names_for_as_the_source_of_the_tool_and_keeps_the_preset(tmp_path: Path,
                                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    model = Owner([9])
    _route(monkeypatch, model)
    ahead = tmp_path / "ahead.json"
    ahead.write_text(json.dumps({"answers": {"must": "check the order"}, "confirmed": True}), encoding="utf-8")
    assert cli.main([*BASE, "--for", "Claude Code", "--answers", str(ahead), "--preset", "efficient",
                     "--out", str(tmp_path / "o")]) == live_cli.EXIT_OK
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["interview_from"] == "answers file; the tool from --for"
    assert record["interview_preset"] == "efficient"


def test_the_interview_source_is_named_for_every_way_it_can_be_answered() -> None:
    from proofhouse import make_interview as mi
    assert mi.answered_by(mi.FileInterviewer(None, "Claude Code")) == "--for"
    assert mi.answered_by(mi.FileInterviewer(None, "voice: kokoro", target_from="the service flags")) == "the service flags"
    terminal = mi.TerminalInterviewer(input, print, "Claude Code")
    assert mi.answered_by(terminal) == "terminal; the tool from --for"
    assert mi.answered_by(mi.TerminalInterviewer(input, print)) == "terminal"
    assert mi.answered_by(None) == "none" and mi.answered_by(object()) == "caller"
    assert mi.answered_by(terminal, shared=True) == "launch"


def test_a_pause_with_for_given_uses_the_same_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                        capsys: pytest.CaptureFixture[str]) -> None:
    _route(monkeypatch, Owner([9]))
    assert cli.main([*BASE, "--for", "Claude Code", "--out", str(tmp_path / "o")]) == live_cli.EXIT_WAITING
    assert "waiting for your answers" in capsys.readouterr().out


def test_a_site_with_no_for_asks_where_it_will_be_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = Owner([9])
    _route(monkeypatch, model)
    folder = tmp_path / "o"
    code = cli.main(["make", "a site for a bakery", "--kind", "site", "--provider", "ollama", "--model", "m",
                     "--out", str(folder)])
    assert code == live_cli.EXIT_WAITING and model.calls == []
    assert "Where will the site be published?" in (folder / "questions.md").read_text(encoding="utf-8")


def test_a_launch_with_no_terminal_pauses_before_any_part_is_made(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                  capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[str] = []

    def model(request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You plan product launches"):
            calls.append("plan")
            content = json.dumps({"name": "bakery", "parts": [{"kind": "prompt", "brief": "a greeting prompt"}]})
        elif text.startswith("You are an expert prompt engineer. You generate"):
            calls.append("questions")
            content = json.dumps([{"id": "audience", "text": "Who is it for?", "type": "text"}])
        else:
            calls.append("other")
            content = "x"
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    monkeypatch.setattr(live, "_default_transport", model, raising=False)
    real = launch.run_launch
    monkeypatch.setattr(launch, "run_launch", lambda *a, **k: real(*a, **{**k, "transport": model}))
    folder = tmp_path / "l"
    code = cli.main(["make", "launch a bakery", "--kind", "launch", "--provider", "ollama", "--model", "m",
                     "--out", str(folder)])
    assert code == live_cli.EXIT_WAITING
    assert f"--answers {folder / 'answers.json'}" in capsys.readouterr().out
    assert "other" not in calls  # no part written blind
    assert (folder / "questions.md").is_file()


def test_a_part_made_inside_a_launch_records_that_its_interview_came_from_the_launch(tmp_path: Path) -> None:
    model = Owner([9])

    class FromLaunch:
        def target(self) -> str | None:
            return "Claude Code"

        def answers(self, questions: list) -> dict[str, str] | None:
            return {q.id: "check the order" for q in questions}

        def confirm(self, understood: str, corrections: list[str]) -> bool | str | None:
            return True

    make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o",
              transport=model, interviewer=FromLaunch(), shared="- Who is it for: bakery staff")
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["interview_from"] == "launch"


def test_a_make_called_from_code_with_no_interviewer_says_so_in_the_record(tmp_path: Path) -> None:
    model = Owner([9])
    make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model)
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["interview_from"] == "none"


def test_an_answers_file_left_empty_says_why_it_is_still_waiting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                 capsys: pytest.CaptureFixture[str]) -> None:
    _route(monkeypatch, Owner([9]))
    folder = tmp_path / "o"
    answers = folder / "answers.json"
    assert cli.main([*BASE, "--for", "Claude Code", "--out", str(folder)]) == live_cli.EXIT_WAITING
    capsys.readouterr()
    assert cli.main([*BASE, "--answers", str(answers)]) == live_cli.EXIT_WAITING
    assert "decide_for_me" in capsys.readouterr().out
    assert cli.main([*BASE, "--answers", str(answers), "--json"]) == live_cli.EXIT_WAITING
    assert "decide_for_me" in json.loads(capsys.readouterr().out)["note"]
