"""The judge marks each thing that was asked for as met or not met, and an unreadable judge is never silent."""
from __future__ import annotations

import json
from pathlib import Path

from proofhouse import live, make

from test_make_interview import Answers, Owner


class Judged(Owner):
    """An Owner whose judge replies are given word for word, and which keeps every prompt the judge and reviser saw."""

    def __init__(self, replies: list[str]) -> None:
        super().__init__([9])
        self.replies = list(replies)
        self.judge_saw: list[str] = []
        self.revise_saw: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You judge AI work"):
            self.calls.append("judge")
            self.judge_saw.append(text)
            return live.Response(200, {"choices": [{"message": {"content": self.replies.pop(0)}}],
                                       "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        if text.startswith("Improve the"):
            self.revise_saw.append(text)
        return super().__call__(request)


def _reply(score: int, limit_met: bool) -> str:
    return json.dumps({"score": score, "fix": "state the 30 day limit", "missing": [], "asked": [
        {"item": "Confirms the order number", "met": True, "why": "step 1 asks for it"},
        {"item": "Refuses refunds after 30 days", "met": limit_met,
         "why": "the limit is stated" if limit_met else "the limit is never mentioned"},
    ]})


def _make(tmp_path: Path, model: Judged, rounds: int = 3) -> make.MakeResult:
    return make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model,
                     rounds=rounds, interviewer=Answers("Claude Code", {"audience": "Just me", "must": "check"}, [True]))


def test_each_asked_for_item_is_marked_and_the_unmet_ones_go_to_the_reviser(tmp_path: Path) -> None:
    model = Judged([_reply(5, False), _reply(9, True)])
    made = _make(tmp_path, model)
    assert made.best_version == 2 and made.asked_for == ["Confirms the order number", "Refuses refunds after 30 days"]
    assert '"asked"' in model.judge_saw[0]
    # the reviser is told every item that was not met, with the judge's reason, and not the ones that were
    assert "NOT MET" in model.revise_saw[0] and "Refuses refunds after 30 days: the limit is never mentioned" in model.revise_saw[0]
    assert "Confirms the order number" not in model.revise_saw[0].split("REQUEST:")[0]
    # later rounds are judged against the same list, so versions can be compared item by item
    assert "1. Confirms the order number\n2. Refuses refunds after 30 days" in model.judge_saw[1]
    assert [[a["met"] for a in r.asked] for r in made.rounds] == [[True, False], [True, True]]
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["asked_for"] == made.asked_for
    assert record["rounds"][0]["asked"][1] == {"item": "Refuses refunds after 30 days", "met": False,
                                               "why": "the limit is never mentioned"}


def test_a_judge_that_gives_no_list_still_works_as_before(tmp_path: Path) -> None:
    model = Judged([json.dumps({"score": 9, "missing": [], "fix": "none"})])
    made = _make(tmp_path, model)
    assert made.best_score == 9 and made.asked_for == [] and made.rounds[0].asked == [] and made.notes == []


def test_an_unreadable_judge_reply_is_asked_for_once_more(tmp_path: Path) -> None:
    model = Judged(["Looks great to me!", _reply(9, True)])
    made = _make(tmp_path, model)
    assert model.calls.count("judge") == 2 and made.best_score == 9 and made.notes == []
    assert "could not be read" in model.judge_saw[1]


def test_a_judge_that_stays_unreadable_is_said_out_loud_and_recorded(tmp_path: Path) -> None:
    model = Judged(["Looks great to me!", "Still great."])
    made = _make(tmp_path, model, rounds=1)
    assert model.calls.count("judge") == 2 and made.best_score is None and made.best_version == 1
    assert len(made.notes) == 1 and "version 1" in made.notes[0] and "could not be read" in made.notes[0]
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["notes"] == made.notes and record["rounds"][0]["judge_unreadable"] is True
