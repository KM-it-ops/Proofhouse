from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

_OBSERVATION_TYPES = (bool, int, float, str)


@dataclass(frozen=True)
class DatasetCase:
    case_id: str
    req_ids: tuple[str, ...]
    observations: dict[str, bool | float | str]
    # Digest of the candidate these observations were produced from, when the
    # dataset declares one. ``None`` means the observations are unbound.
    candidate_digest: str | None = None


def _reject_constant(name: str) -> object:
    raise ValueError(f"non-finite number {name}")


def _parse_line(line: str, line_no: int) -> DatasetCase:
    try:
        raw = json.loads(line, parse_constant=_reject_constant)
    except ValueError as exc:
        raise ValueError(f"line {line_no}: invalid JSON ({exc})") from None
    if not isinstance(raw, dict):
        raise ValueError(f"line {line_no}: each case must be a JSON object")
    case_id = raw.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError(f"line {line_no}: case_id must be a non-empty string")
    req_ids = raw.get("req_ids")
    if not isinstance(req_ids, list) or not req_ids or not all(
        isinstance(req_id, str) and req_id.startswith("REQ-") for req_id in req_ids
    ):
        raise ValueError(f"line {line_no}: req_ids must be non-empty REQ-*")
    if len(set(req_ids)) != len(req_ids):
        raise ValueError(f"line {line_no}: req_ids contains a duplicate")
    observations = raw.get("observations")
    if not isinstance(observations, dict):
        raise ValueError(f"line {line_no}: observations must be a JSON object")
    for key, value in observations.items():
        if not isinstance(value, _OBSERVATION_TYPES) or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError(f"line {line_no}: observation {key!r} must be a finite number, boolean or string")
    candidate = raw.get("candidate_digest")
    if candidate is not None and (not isinstance(candidate, str) or not candidate.strip()):
        raise ValueError(f"line {line_no}: candidate_digest must be a non-empty string when present")
    return DatasetCase(case_id=case_id, req_ids=tuple(req_ids), observations=dict(observations), candidate_digest=candidate)


def load_dataset(path: Path) -> tuple[DatasetCase, ...]:
    """Load JSONL cases. Duplicate ``case_id`` values are rejected, never merged."""
    cases: list[DatasetCase] = []
    seen: dict[str, int] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = _parse_line(line, line_no)
        if case.case_id in seen:
            raise ValueError(
                f"line {line_no}: duplicate case_id {case.case_id!r} (first seen on line {seen[case.case_id]})"
            )
        seen[case.case_id] = line_no
        cases.append(case)
    if not cases:
        raise ValueError("dataset empty")
    return tuple(cases)
