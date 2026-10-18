"""The goal picker: ``proofhouse "<goal>"`` picks the right kind of thing to make.

The answer key is ``docs/overseer-test-set.md``, read from the doc itself so
the test and the doc cannot drift apart. Its pass rules:

- the pick is the "Should be" label, or an "Also fair" one with its reason;
- for the ambiguous goals, a person who is there may instead be asked one
  short question; with nobody there, the safer pick must still pass.

A question on a clear goal fails: asking on every goal would dodge the pick.
The built-in rules are graded on every goal. The model path is checked for its
wiring only, with a stand-in model.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from proofhouse import cli, live, make, spend
from proofhouse.compiler.orchestration import overseer
from proofhouse.compiler.orchestration.route import _ALLOWED, MAKE_KINDS, RouteDecision

ANSWER_KEY = Path(__file__).resolve().parents[3] / "docs" / "overseer-test-set.md"
MAX_QUESTION_CHARS = 160


@dataclass(frozen=True)
class Goal:
    number: int
    objective: str
    label: str
    also_fair: tuple[str, ...]
    ambiguous: bool


def read_goals(path: Path) -> list[Goal]:
    """Every row of the answer-key table: ``| # | Objective | Should be | Also fair | Today's router | Reason |``."""
    goals = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not cells[0].isdigit():
            continue
        number, objective, label, fair, _today, reason = cells
        also_fair = tuple(item.strip() for item in fair.split(",") if item.strip() not in {"", "-"})
        goals.append(Goal(int(number), objective, label, also_fair, reason.startswith("Ambiguous")))
    return goals


def _has_reason(rationale: str) -> bool:
    return len(rationale.split()) >= 3


def miss_unattended(goal: Goal, decision: RouteDecision) -> str | None:
    """Why the pick fails the answer key, or ``None`` when it passes."""
    if decision.artifact_class == goal.label:
        return None
    if decision.artifact_class in goal.also_fair and _has_reason(decision.rationale):
        return None
    fair = f" (also fair: {', '.join(goal.also_fair)})" if goal.also_fair else ""
    return f"#{goal.number}: got {decision.artifact_class} ({decision.rationale}); should be {goal.label}{fair}"


def miss_with_person(goal: Goal, decision: RouteDecision, asked: list[tuple[str, tuple[str, ...]]]) -> str | None:
    if not asked:
        return miss_unattended(goal, decision)
    if len(asked) > 1:
        return f"#{goal.number}: asked {len(asked)} questions; one at most"
    if not goal.ambiguous:
        return f"#{goal.number}: asked {asked[0][0]!r} on a goal that is not ambiguous"
    question, options = asked[0]
    if not question.strip().endswith("?") or len(question) > MAX_QUESTION_CHARS:
        return f"#{goal.number}: {question!r} is not one short question"
    if len(set(options)) < 2 or any(option not in _ALLOWED for option in options):
        return f"#{goal.number}: the question's options {options!r} are not two or more known kinds"
    return None


GOALS = read_goals(ANSWER_KEY)
# The rules were fitted to these 32 goals, so the bar is three in four, not all.
MIN_PASSING = 24


class Person:
    """Someone at the terminal who hears the question and names no kind."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, tuple[str, ...]]] = []

    def __call__(self, question: str, options: tuple[str, ...]) -> str:
        self.asked.append((question, options))
        return ""


def _report(misses: list[str]) -> str:
    return f"{len(GOALS) - len(misses)} of {len(GOALS)} goals pass:\n" + "\n".join(misses)


def test_the_answer_key_is_read_from_the_doc() -> None:
    assert [goal.number for goal in GOALS] == list(range(1, 33))
    assert [goal.number for goal in GOALS if goal.ambiguous] == [27, 28, 29, 30, 31, 32]
    assert GOALS[0].label == "loop" and GOALS[30].also_fair == ("site", "mcp", "prompt")
    # The router knows every answer the doc accepts, and make's kinds are its kinds.
    assert {goal.label for goal in GOALS} | {kind for goal in GOALS for kind in goal.also_fair} <= set(_ALLOWED)
    assert MAKE_KINDS == (*make.KINDS, "video", "launch")


def test_when_nobody_is_there_the_built_in_rules_pass_enough_of_the_answer_key() -> None:
    misses = [miss for goal in GOALS if (miss := miss_unattended(goal, overseer.decide(goal.objective))) is not None]
    assert len(GOALS) - len(misses) >= MIN_PASSING, _report(misses)


def test_with_a_person_there_the_rules_ask_only_on_ambiguous_goals() -> None:
    misses = []
    for goal in GOALS:
        person = Person()
        decision = overseer.decide(goal.objective, ask=person)
        if (miss := miss_with_person(goal, decision, person.asked)) is not None:
            misses.append(miss)
    assert len(GOALS) - len(misses) >= MIN_PASSING, _report(misses)


def test_the_front_door_acts_on_the_same_pick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for goal in GOALS:
        result = overseer.oversee(goal.objective, case_dir=tmp_path / f"case-{goal.number}")
        assert result.decision == overseer.decide(goal.objective), goal.number


def test_unattended_a_goal_with_a_question_says_it_took_the_safer_pick(monkeypatch: pytest.MonkeyPatch) -> None:
    two_ways = RouteDecision("loop", "repeats on its own", False, "Should it run on a timer or on an event?", ("loop", "hook"))
    monkeypatch.setattr(overseer, "route", lambda request: two_ways)
    decision = overseer.decide("anything")
    assert decision.artifact_class == "loop" and "safer pick" in decision.rationale
    person = Person()
    assert overseer.decide("anything", ask=person).artifact_class == "loop"
    assert person.asked == [(two_ways.question, ("loop", "hook"))]
    assert overseer.decide("anything", ask=lambda q, o: "on an event, so a hook").artifact_class == "hook"
    assert overseer.decide("anything", ask=lambda q, o: "2").artifact_class == "hook"


@pytest.mark.parametrize(("old", "new"), [("subagent", "agent"), ("MCP", "mcp"), ("media", "video")])
def test_old_class_names_still_force_a_class(old: str, new: str) -> None:
    assert overseer.decide("anything", {"artifact_class": old}).artifact_class == new


# The model path, with a stand-in model: wiring only, not the quality of any real model's picks.


class Model:
    """A stand-in model that gives one fixed reply and keeps every prompt it was sent."""

    def __init__(self, reply: dict | str) -> None:
        self.reply = reply if isinstance(reply, str) else json.dumps(reply)
        self.sent: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        self.sent.append(" ".join(m["content"] for m in json.loads(request.body_bytes)["messages"]))
        return live.Response(200, {"choices": [{"message": {"content": self.reply}}],
                                   "usage": {"prompt_tokens": 60, "completion_tokens": 20}})


def _gate_spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    real = spend.send_within_ceiling

    def spy(*args, **kwargs):
        seen.append(kwargs["model"])
        return real(*args, **kwargs)

    monkeypatch.setattr(spend, "send_within_ceiling", spy)
    return seen


def test_with_a_model_set_up_the_model_picks_through_the_spend_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate_spy(monkeypatch)
    model = Model({"kind": "loop", "reason": "it runs every week with nobody watching", "question": "", "options": []})
    decision = overseer.decide("a weekly digest of new releases", provider="ollama", model="m", transport=model)
    assert decision.artifact_class == "loop" and decision.question is None
    assert "it runs every week with nobody watching" in decision.rationale and "ollama/m" in decision.rationale
    assert gate == ["m"] and len(model.sent) == 1
    assert "a weekly digest of new releases" in model.sent[0]
    assert all(kind in model.sent[0] for kind in _ALLOWED)


def test_the_models_question_is_asked_once_when_a_person_is_there() -> None:
    model = Model({"kind": "app", "reason": "people ask it questions", "question": "Is it for people or for agents?",
                   "options": ["app", "MCP"]})
    person = Person()
    decision = overseer.decide("x", provider="ollama", model="m", transport=model, ask=person)
    assert person.asked == [("Is it for people or for agents?", ("app", "mcp"))]
    assert decision.artifact_class == "app"
    unattended = overseer.decide("x", provider="ollama", model="m", transport=model)
    assert unattended.artifact_class == "app" and "safer pick" in unattended.rationale


@pytest.mark.parametrize(
    "reply",
    [{"kind": "poster", "reason": "?"}, "I think a loop would be best.", {"reason": "no kind given"}],
)
def test_a_model_answer_that_cannot_be_used_falls_back_to_the_rules_and_says_so(reply: dict | str) -> None:
    rules = overseer.decide("build a marketing website")
    decision = overseer.decide("build a marketing website", provider="ollama", model="m", transport=Model(reply))
    assert decision.artifact_class == rules.artifact_class
    assert "built-in rules" in decision.rationale and "model's pick was not used" in decision.rationale


def test_a_refused_call_sends_nothing_and_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-goal-picker-test-key")
    model = Model({"kind": "loop", "reason": "x"})
    decision = overseer.decide("build a marketing website", provider="groq", model="m", transport=model)
    assert model.sent == []  # a paid provider with no spending limit is refused before sending
    assert decision.artifact_class == overseer.decide("build a marketing website").artifact_class
    assert "--max-cost-usd" in decision.rationale and "gsk-goal-picker-test-key" not in decision.rationale


def test_a_forced_class_skips_the_model() -> None:
    model = Model({"kind": "loop", "reason": "x"})
    decision = overseer.decide("anything", {"artifact_class": "skill"}, provider="ollama", model="m", transport=model)
    assert decision.artifact_class == "skill" and model.sent == []


def test_the_front_door_flags_reach_the_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    model = Model({"kind": "loop", "reason": "it repeats on its own"})
    monkeypatch.setattr(live, "_httpx_post", model)
    code = cli.main(["a weekly digest of new releases", "--provider", "ollama", "--model", "m", "--json"], prog="proofhouse")
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert json.loads(captured.out)["artifact_class"] == "loop" and len(model.sent) == 1
    assert "no part yet for loop" in captured.err


def test_the_front_door_wants_a_model_with_a_provider(capsys) -> None:
    code = cli.main(["a weekly digest of new releases", "--provider", "ollama"], prog="proofhouse")
    assert code == 2 and "--model" in capsys.readouterr().err
