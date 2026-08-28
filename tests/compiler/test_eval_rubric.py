from pathlib import Path

from promptrig.compiler.eval_dataset import DatasetCase, load_dataset
from promptrig.compiler.eval_rubric import load_rubric, score_case


CASES = Path("tests/compiler/fixtures/mission_027/cases.jsonl")
RUBRIC = Path("tests/compiler/fixtures/mission_027/rubric.json")


def test_score_pass_and_fail_cases() -> None:
    rubric = load_rubric(RUBRIC)
    cases = load_dataset(CASES)
    pass_scores = score_case(rubric, cases[0])
    assert pass_scores == {"compile": 1.0, "security": 1.0}
    fail_scores = score_case(rubric, cases[1])
    assert fail_scores["compile"] == 0.0
    assert fail_scores["security"] == 1.0


def test_missing_observation_is_none() -> None:
    rubric = load_rubric(RUBRIC)
    case = DatasetCase("EVC-Z", ("REQ-EVAL-001",), {})
    scores = score_case(rubric, case)
    assert scores["compile"] is None
    assert scores["security"] is None
