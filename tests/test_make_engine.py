"""The make engine: write, try, judge, improve; one spending limit for the whole command; everything kept."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

import proofhouse
from proofhouse import cli, live, make


class ScriptedModel:
    """Answers like a model would, by role, so no network is needed. Scores rise each round."""

    def __init__(self, scores: list[int], skill: bool = False) -> None:
        self.scores = list(scores)
        self.skill = skill
        self.calls: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        body = json.loads(request.body_bytes)
        text = " ".join(m["content"] for m in body["messages"])
        if text.startswith(("You write excellent prompts", "You write agent skills", "You write subagents")):
            role, content = "write", self._artifact(1)
        elif text.startswith("Write one realistic input"):
            role, content = "test input", "A customer asks for a refund on order 42."
        elif text.startswith("You judge AI work"):
            role, content = "judge", json.dumps({"score": self.scores.pop(0), "missing": ["tone"], "fix": "be warmer"})
        elif text.startswith("Improve the"):
            role, content = "revise", self._artifact(len([c for c in self.calls if c == "revise"]) + 2)
        else:
            role, content = "try", "Dear customer, your refund is on its way."
        self.calls.append(role)
        return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}})

    def _artifact(self, n: int) -> str:
        if self.skill == "agent":
            return f"---\nname: refund-agent\ndescription: Handles refunds (v{n}).\n---\nDo refunds well v{n}."
        if self.skill:
            return f"```markdown\n---\nname: refund-helper\ndescription: Use when a customer asks for a refund (v{n}).\n---\nSteps for v{n}.\n```"
        return f"You are a support agent. Version {n}."


def test_a_prompt_is_written_tried_judged_and_improved_until_the_target(tmp_path: Path) -> None:
    model = ScriptedModel([5, 7, 9])
    made = make.make("a prompt that answers refund emails warmly", provider_id="ollama", model="llama3",
                     rounds=5, out_dir=tmp_path / "out", transport=model)
    assert made.stopped == "reached score 9 (target 9)"
    assert [r.score for r in made.rounds] == [5, 7, 9] and made.best_version == 3
    assert (tmp_path / "out" / "final.md").read_text(encoding="utf-8") == "You are a support agent. Version 3.\n"
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["final.md", "record.json", "v1.md", "v2.md", "v3.md"]
    assert model.calls == ["write", "test input", "try", "judge", "revise", "try", "judge", "revise", "try", "judge"]
    record = json.loads((tmp_path / "out" / "record.json").read_text(encoding="utf-8"))
    assert record["best_score"] == 9 and len(record["calls"]) == 10
    assert "advice, not proof" in record["judge_note"]
    assert record["proofhouse_version"] == proofhouse.__version__


def test_the_best_version_wins_when_rounds_run_out(tmp_path: Path) -> None:
    made = make.make("x", provider_id="ollama", model="m", rounds=3, out_dir=tmp_path / "o", transport=ScriptedModel([6, 8, 7]))
    assert made.stopped == "rounds used up" and made.best_version == 2 and made.best_score == 8
    assert (tmp_path / "o" / "final.md").read_text(encoding="utf-8") == "You are a support agent. Version 2.\n"


def test_your_own_test_input_is_used(tmp_path: Path) -> None:
    model = ScriptedModel([10])
    make.make("x", provider_id="ollama", model="m", test_input="my real input", out_dir=tmp_path / "o", transport=model)
    assert "test input" not in model.calls


def test_one_spending_limit_covers_the_whole_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert cli.main(["providers", "price", "groq", "m", "--input", "1000", "--output", "1000"]) == 0
    model = ScriptedModel([1, 1, 1, 1, 1])
    made = make.make("x", provider_id="groq", model="m", rounds=5, max_cost_usd="2.5",
                     max_output_tokens=256, out_dir=tmp_path / "o", transport=model)
    assert made.stopped == "spending limit reached"
    assert made.spent_usd <= Decimal("2.5")
    assert len(model.calls) < 10  # stopped before the rounds ran out


def test_a_paid_provider_needs_a_limit_and_a_known_provider(tmp_path: Path) -> None:
    with pytest.raises(make.MakeError):
        make.make("x", provider_id="openai", model="m", out_dir=tmp_path / "a")
    with pytest.raises(make.MakeError):
        make.make("x", provider_id="nope", model="m", out_dir=tmp_path / "b")
    with pytest.raises(make.MakeError):
        make.make("x", provider_id="ollama", model="m", kind="video", out_dir=tmp_path / "c")


def test_a_skill_comes_out_installable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    made = make.make("a skill that handles refund requests", provider_id="ollama", model="m", kind="skill",
                     out_dir=tmp_path / "s", transport=ScriptedModel([9], skill=True))
    skill_md = tmp_path / "s" / "refund-helper" / "SKILL.md"
    assert made.best_version == 1 and skill_md.is_file()
    assert skill_md.read_text(encoding="utf-8").startswith("---\nname: refund-helper\n")
    assert cli.main(["install-skill", "--bundle", str(tmp_path / "s" / "refund-helper"), "--host", "claude"]) == 0


def test_a_judge_that_does_not_answer_in_json_does_not_crash_the_run(tmp_path: Path) -> None:
    class Rambling(ScriptedModel):
        def __call__(self, request: live.Request) -> live.Response:
            reply = super().__call__(request)
            if self.calls[-1] == "judge":
                reply.payload["choices"][0]["message"]["content"] = "It is pretty good overall."
            return reply

    made = make.make("x", provider_id="ollama", model="m", rounds=2, out_dir=tmp_path / "o", transport=Rambling([1, 1]))
    assert [r.score for r in made.rounds] == [None, None] and made.best_version == 2


def test_cli_make_prints_where_everything_is(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    model = ScriptedModel([9])
    monkeypatch.setattr(live, "_httpx_post", model)
    code = cli.main(["make", "a refund prompt", "--provider", "ollama", "--model", "m", "--out", str(tmp_path / "o")])
    out = capsys.readouterr().out
    assert code == 0 and "made: version 1 (judge score 9/10)" in out and str(tmp_path / "o") in out


def test_a_made_subagent_installs_into_claude_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    made = make.make("an agent that handles refunds", provider_id="ollama", model="m", kind="agent",
                     out_dir=tmp_path / "a", transport=ScriptedModel([9], skill="agent"))
    agent = tmp_path / "a" / "refund-agent.md"
    assert made.best_version == 1 and agent.is_file()
    assert cli.main(["install", "agent", str(agent), "--into", "claude"]) == 0
    assert (home / ".claude" / "agents" / "refund-agent.md").is_file()
