"""Rubric matching is type-strict (evidence-integrity review, still open on 0.7.0).

Python says ``1 == True`` and ``0 == False``, so a rubric expecting ``true`` passed an observation of
``1``. A true/false expectation matches only a true/false observation; numbers still compare as
numbers (``1`` matches ``1.0``); text matches only text.
"""
from __future__ import annotations

import pytest

from proofhouse.compiler.eval_dataset import DatasetCase
from proofhouse.compiler.eval_rubric import Rubric, RubricCriterion, score_case


def _score(expected: object, observed: object) -> float | None:
    rubric = Rubric("r", "1", (RubricCriterion(criterion_id="c", field="f", expected=expected),))  # type: ignore[arg-type]
    case = DatasetCase(case_id="k", req_ids=("REQ-1",), observations={"f": observed})
    return score_case(rubric, case)["c"]


@pytest.mark.parametrize(
    ("expected", "observed"),
    [(True, 1), (False, 0), (1, True), (0, False), (1.0, True), (True, 1.0), ("1", 1), (1, "1"), (True, "true")],
)
def test_values_of_different_kinds_do_not_match(expected: object, observed: object) -> None:
    assert _score(expected, observed) == 0.0


@pytest.mark.parametrize(
    ("expected", "observed"),
    [(True, True), (False, False), (1, 1), (1, 1.0), (1.5, 1.5), ("ok", "ok")],
)
def test_values_of_the_same_kind_still_match(expected: object, observed: object) -> None:
    assert _score(expected, observed) == 1.0


def test_missing_observation_is_still_unscored() -> None:
    rubric = Rubric("r", "1", (RubricCriterion(criterion_id="c", field="f", expected=True),))
    case = DatasetCase(case_id="k", req_ids=("REQ-1",), observations={})
    assert score_case(rubric, case)["c"] is None
