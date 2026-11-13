"""The closing lines of a make say what was met, what was not, how the winner was picked, and what to doubt."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import cli, live, live_cli, make
from proofhouse.optimize import cli as optimize_cli

from test_make_asked_for import Judged, _reply
from test_make_interview import Answers, Owner


@pytest.fixture(autouse=True)
def _no_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(optimize_cli, "_stdin_is_terminal", lambda: False)


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model: Owner, *extra: str) -> int:
    real = make.make
    monkeypatch.setattr(make, "make", lambda *a, **k: real(*a, **{**k, "transport": model}))
    ahead = tmp_path / "ahead.json"
    ahead.write_text(json.dumps({"for": "Claude Code", "answers": {"must": "check the order"}, "confirmed": True}),
                     encoding="utf-8")
    return cli.main(["make", "a skill for refunds", "--kind", "skill", "--provider", "ollama", "--model", "m",
                     "--answers", str(ahead), "--out", str(tmp_path / "o"), *extra])


def test_the_closing_lines_say_what_was_met_and_what_was_not(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                             capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(tmp_path, monkeypatch, Judged([_reply(5, False), _reply(6, False)]), "--rounds", "2") == live_cli.EXIT_OK
    out = capsys.readouterr().out
    assert "made: version 2 (judge score 6/10)" in out  # the line people already rely on stays
    assert "asked for: 1 of 2 met" in out
    assert "not met: Refuses refunds after 30 days (the limit is never mentioned)" in out
    assert "version 2 was picked out of 2" in out
    assert "advice, not proof" in out
    assert "same model wrote it and judged it" in out and "--judge" in out


def test_everything_met_and_one_version_says_so_briefly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                        capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(tmp_path, monkeypatch, Judged([_reply(9, True)])) == live_cli.EXIT_OK
    out = capsys.readouterr().out
    assert "asked for: 2 of 2 met" in out and "not met:" not in out and "was picked out of" not in out


def test_a_judge_that_gave_no_list_adds_no_asked_for_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(tmp_path, monkeypatch, Owner([9])) == live_cli.EXIT_OK
    assert "asked for:" not in capsys.readouterr().out


def test_an_unreadable_judge_is_said_in_the_closing_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    _run(tmp_path, monkeypatch, Judged(["Great!", "Still great."]), "--rounds", "1")
    out = capsys.readouterr().out
    assert "note: The judge's reply for version 1 could not be read" in out
    assert "advice, not proof" not in out  # there is no score to warn about


def test_the_json_summary_carries_the_marks_and_the_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    _run(tmp_path, monkeypatch, Judged([_reply(5, False)]), "--rounds", "1", "--json")
    summary = json.loads(capsys.readouterr().out)
    assert [a["met"] for a in summary["asked_for"]] == [True, False]
    assert any("advice, not proof" in note for note in summary["notes"])


class CutShort(Owner):
    """An Owner whose written replies stop at the output limit."""

    def __call__(self, request: live.Request) -> live.Response:
        body = json.loads(request.body_bytes)
        self.limit = body.get("max_tokens") or body.get("max_completion_tokens")
        reply = super().__call__(request)
        if self.calls[-1] == "write":
            reply.payload["choices"][0]["finish_reason"] = "length"
        return reply


def test_a_reply_cut_off_at_the_limit_is_said_once_with_the_way_to_raise_it(tmp_path: Path) -> None:
    made = make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=CutShort([9]),
                     max_output_tokens=3000,
                     interviewer=Answers("Claude Code", {"audience": "Just me", "must": "check"}, [True]))
    cut = [note for note in made.notes if "stopped at the output limit" in note]
    assert len(cut) == 1 and "3000" in cut[0] and "--max-output-tokens" in cut[0]


def test_the_command_passes_the_output_limit_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                capsys: pytest.CaptureFixture[str]) -> None:
    model = CutShort([9])
    assert _run(tmp_path, monkeypatch, model, "--max-output-tokens", "5000") == live_cli.EXIT_OK
    assert model.limit == 5000
    assert "stopped at the output limit (5000 tokens)" in capsys.readouterr().out
