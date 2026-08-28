from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .eval_dataset import DatasetCase


@dataclass(frozen=True)
class RubricCriterion:
    criterion_id: str
    field: str
    expected: bool | float | str


@dataclass(frozen=True)
class Rubric:
    rubric_id: str
    version: str
    criteria: tuple[RubricCriterion, ...]


def load_rubric(path: Path) -> Rubric:
    raw = json.loads(path.read_text(encoding="utf-8"))
    criteria = tuple(
        RubricCriterion(
            criterion_id=str(item["criterion_id"]),
            field=str(item["field"]),
            expected=item["expected"],
        )
        for item in raw["criteria"]
    )
    if not criteria:
        raise ValueError("rubric has no criteria")
    return Rubric(str(raw["rubric_id"]), str(raw["version"]), criteria)


def score_case(rubric: Rubric, case: DatasetCase) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for criterion in rubric.criteria:
        if criterion.field not in case.observations:
            out[criterion.criterion_id] = None
            continue
        out[criterion.criterion_id] = (
            1.0 if case.observations[criterion.field] == criterion.expected else 0.0
        )
    return out
