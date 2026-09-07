from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetCase:
    case_id: str
    req_ids: tuple[str, ...]
    observations: dict[str, bool | float | str]


def load_dataset(path: Path) -> tuple[DatasetCase, ...]:
    cases: list[DatasetCase] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        raw = json.loads(line)
        req_ids = tuple(raw["req_ids"])
        if not req_ids or not all(
            isinstance(req_id, str) and req_id.startswith("REQ-")
            for req_id in req_ids
        ):
            raise ValueError(f"line {line_no}: req_ids must be non-empty REQ-*")
        cases.append(
            DatasetCase(
                case_id=str(raw["case_id"]),
                req_ids=req_ids,
                observations=dict(raw["observations"]),
            )
        )
    if not cases:
        raise ValueError("dataset empty")
    return tuple(cases)
