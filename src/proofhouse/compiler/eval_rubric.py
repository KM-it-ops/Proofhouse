from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .eval_dataset import DatasetCase, reject_duplicate_keys


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
    """Load a rubric. Duplicate ``criterion_id`` values are rejected, never merged."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"rubric is not valid JSON ({exc.msg})") from None
    except ValueError as exc:
        raise ValueError(f"rubric is not valid JSON ({exc})") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("criteria"), list):
        raise ValueError("rubric must be an object with a criteria array")
    for key in ("rubric_id", "version"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise ValueError(f"rubric {key} must be a non-empty string")
    criteria: list[RubricCriterion] = []
    seen: set[str] = set()
    for index, item in enumerate(raw["criteria"]):
        if not isinstance(item, dict) or not all(key in item for key in ("criterion_id", "field", "expected")):
            raise ValueError(f"rubric criterion {index} must have criterion_id, field and expected")
        criterion_id = str(item["criterion_id"])
        if criterion_id in seen:
            raise ValueError(f"rubric criterion {index}: duplicate criterion_id {criterion_id!r}")
        seen.add(criterion_id)
        criteria.append(RubricCriterion(criterion_id=criterion_id, field=str(item["field"]), expected=item["expected"]))
    if not criteria:
        raise ValueError("rubric has no criteria")
    return Rubric(raw["rubric_id"], raw["version"], tuple(criteria))


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
