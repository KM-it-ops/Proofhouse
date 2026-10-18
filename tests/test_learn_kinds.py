"""A kind Proofhouse does not know is researched and learned, never refused and never swapped for a known kind."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import addons, cli, learn, live, make, spend
from proofhouse.compiler.orchestration import overseer
from proofhouse.compiler.orchestration.route import RouteRequest, _forced_class, route

RESEARCH = {
    "what_it_is": "A press kit is a ready-made bundle that gives journalists the facts, quotes and images for a story.",
    "write": "You make press kits. Include a one-paragraph summary, a fact sheet, two quotes, founder bios and a "
             "media contact. Output only the finished press kit.",
    "subject": "Press kit",
    "sources": ["https://example.org/what-is-a-press-kit", "not a web address"],
}


class Model:
    """A stand-in model that answers by what each prompt asks, and keeps every prompt it was sent."""

    def __init__(self, research: dict | str = RESEARCH) -> None:
        self.research = research if isinstance(research, str) else json.dumps(research)
        self.sent: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        self.sent.append(text)
        if text.startswith("Proofhouse makes many kinds"):
            content = self.research
        elif text.startswith("You judge AI work"):
            assert "PRESS KIT:" in text
            content = json.dumps({"score": 10, "missing": [], "fix": ""})
        else:
            assert text.startswith("You make press kits") and "What a press-kit is:" in text
            content = "BREW PRESS KIT\nSummary: Brew makes coffee in one tap."
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 10, "completion_tokens": 10}})


def _gate_spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    real = spend.send_within_ceiling

    def spy(*args, **kwargs):
        body = args[0] if isinstance(args[0], dict) else json.loads(args[0])
        seen.append(body["messages"][0]["content"][:27])
        return real(*args, **kwargs)

    monkeypatch.setattr(spend, "send_within_ceiling", spy)
    return seen


def test_a_new_kind_is_researched_through_the_spend_gate_then_made(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate_spy(monkeypatch)
    model = Model()
    made = make.make("a press kit for Brew's launch", provider_id="ollama", model="m", kind="press-kit",
                     out_dir=tmp_path / "out", transport=model)
    assert made.best_score == 10 and made.learned is not None
    assert (tmp_path / "out" / "final.md").read_text(encoding="utf-8").startswith("BREW PRESS KIT")
    assert [c.role for c in made.calls] == ["research", "write", "judge"]
    assert gate[0] == "Proofhouse makes many kinds" and len(gate) == 3  # every call, the research too
    record = json.loads((tmp_path / "out" / "record.json").read_text(encoding="utf-8"))
    assert record["kind"] == "press-kit" and record["kind_from"]["learned_this_run"] is True
    assert record["kind_from"]["learned_by"] == "ollama/m"
    assert record["kind_from"]["sources"] == ["https://example.org/what-is-a-press-kit"]
    assert record["kind_from"]["sources_note"] == learn.SOURCES_NOTE
    assert "press-kit" in addons.make_kinds() and addons.make_kinds()["press-kit"]["addon"] == "learned"

    again = Model()
    second = make.make("a press kit for Brew's second launch", provider_id="ollama", model="m", kind="press-kit",
                       out_dir=tmp_path / "again", transport=again)
    assert [c.role for c in second.calls] == ["write", "judge"] and second.learned is None  # learned once
    assert json.loads((tmp_path / "again" / "record.json").read_text(encoding="utf-8"))["kind_from"]["learned_this_run"] is False


def test_the_name_a_person_typed_is_the_kind(tmp_path: Path) -> None:
    made = make.make("a press kit", provider_id="ollama", model="m", kind="Press Kit", out_dir=tmp_path / "o",
                     transport=Model())
    assert made.kind == "press-kit" and made.best_score == 10
    assert learn.kind_name("Subagent") == "subagent" and learn.kind_name("  ") is None and learn.kind_name("!!") is None


@pytest.mark.parametrize("answer", ["I am not sure what that is.", {"what_it_is": "x"}, {"what_it_is": "", "write": "x" * 30},
                                    {"what_it_is": "A thing.", "write": "too short"}])
def test_research_that_cannot_be_used_stops_the_make_and_saves_nothing(tmp_path: Path, answer: dict | str) -> None:
    made = make.make("a press kit", provider_id="ollama", model="m", kind="press-kit", out_dir=tmp_path / "o",
                     transport=Model(answer))
    assert made.stopped.startswith("could not learn what a press-kit is") and made.best_version is None
    assert not learn.pack_path().exists() and not (tmp_path / "o" / "final.md").exists()
    assert json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))["stopped"] == made.stopped


def test_a_paid_research_call_stays_inside_the_spending_limit(tmp_path: Path) -> None:
    with pytest.raises(make.MakeError, match="--max-cost-usd"):
        make.make("a press kit", provider_id="openai", model="m", kind="press-kit", out_dir=tmp_path / "o")
    assert not learn.pack_path().exists()


def test_what_is_not_a_kind_name_or_has_its_own_engine_is_said_plainly(tmp_path: Path) -> None:
    with pytest.raises(make.MakeError, match="a kind is a name"):
        make.make("x", provider_id="ollama", model="m", kind="!!", out_dir=tmp_path / "a")
    with pytest.raises(make.MakeError, match="own engine"):
        make.make("x", provider_id="ollama", model="m", kind="Video", out_dir=tmp_path / "b")


def test_a_pack_that_cannot_be_read_is_kept_aside_not_lost(tmp_path: Path) -> None:
    learn.pack_path().parent.mkdir(parents=True)
    learn.pack_path().write_text("{ broken", encoding="utf-8")
    make.make("a press kit", provider_id="ollama", model="m", kind="press-kit", out_dir=tmp_path / "o", transport=Model())
    kept = list(learn.pack_path().parent.glob("addon.json.unreadable-*"))
    assert len(kept) == 1 and kept[0].read_text(encoding="utf-8") == "{ broken"
    assert "press-kit" in addons.make_kinds()


def test_learning_a_second_kind_keeps_the_first(tmp_path: Path) -> None:
    learn.save(learn.parse("press-kit", json.dumps(RESEARCH), learned_by="ollama/m"))
    learn.save(learn.parse("pitch-deck", json.dumps({**RESEARCH, "write": "You make pitch decks. " * 3}), learned_by="ollama/m"))
    learn.save(learn.parse("press-kit", json.dumps(RESEARCH), learned_by="ollama/other"))
    kinds = addons.make_kinds()
    assert set(kinds) == {"press-kit", "pitch-deck"} and kinds["press-kit"]["learned_by"] == "ollama/other"


# The goal picker and the front door.


def test_a_forced_new_kind_is_kept_not_swapped_for_a_known_one() -> None:
    request = RouteRequest("build a marketing website", {"artifact_class": "Press Kit"})
    decision = route(request)
    assert _forced_class(request) == "press-kit" and decision.artifact_class == "press-kit"
    assert "researches and learns it" in decision.rationale and "proofhouse make --kind press-kit" in decision.rationale


def test_a_forced_new_kind_skips_the_model_pick() -> None:
    model = Model()
    decision = overseer.decide("anything", {"artifact_class": "press-kit"}, provider="ollama", model="m", transport=model)
    assert decision.artifact_class == "press-kit" and model.sent == []


def test_a_learned_kind_is_named_as_known() -> None:
    learn.save(learn.parse("press-kit", json.dumps(RESEARCH), learned_by="ollama/m"))
    assert "a kind from add-on learned" in route(RouteRequest("x", {"artifact_class": "press-kit"})).rationale


def test_text_that_is_not_a_kind_name_says_so_before_the_rules_pick() -> None:
    decision = route(RouteRequest("build a marketing website", {"artifact_class": "???"}))
    assert decision.rationale.startswith("artifact_class='???' is not a kind name;")


def test_the_front_door_learns_a_new_kind_with_the_model_set_up(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate_spy(monkeypatch)
    result = overseer.oversee("a press kit for Brew", {"artifact_class": "press-kit"}, provider="ollama", model="m",
                              transport=Model())
    assert gate == ["Proofhouse makes many kinds"] and "press-kit" in addons.make_kinds()
    [line] = [json.loads(x) for x in overseer.demand_record_path().read_text(encoding="utf-8").splitlines()]
    assert line["status"] == "learned" and line["forced"] is True
    assert 'proofhouse make --kind press-kit "a press kit for Brew" --provider ollama --model m' in line["next"]
    assert result.note == line["next"] and result.case_dir is None


def test_without_a_model_the_front_door_says_it_is_learned_when_first_made() -> None:
    result = overseer.oversee("a press kit for Brew", {"artifact_class": "press-kit"})
    [line] = [json.loads(x) for x in overseer.demand_record_path().read_text(encoding="utf-8").splitlines()]
    assert line["status"] == "to learn" and "researches it the first time you make it" in line["next"]
    assert not learn.pack_path().exists() and result.note == line["next"]


def test_failed_research_at_the_front_door_is_recorded_to_try_again() -> None:
    overseer.oversee("x", {"artifact_class": "press-kit"}, provider="ollama", model="m", transport=Model("no idea"))
    [line] = [json.loads(x) for x in overseer.demand_record_path().read_text(encoding="utf-8").splitlines()]
    assert line["status"] == "to learn" and "tried again when you make it" in line["next"]


def test_make_on_the_command_line_says_what_it_learned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(live, "_httpx_post", Model())
    code = cli.main(["make", "a press kit for Brew", "--kind", "press-kit", "--provider", "ollama", "--model", "m",
                     "--out", str(tmp_path / "o"), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["kind"] == "press-kit" and out["learned"]["sources_note"] == learn.SOURCES_NOTE
